# ctdmate/tools/gen_solar.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import os, json, time, re

# config
try:
    from ctdmate.app import config as CFG
except Exception:
    from ..app import config as CFG  # type: ignore

# RAG + 정규화 + Lint
try:
    from ctdmate.rag.mfds_rag import MFDSRAGTool
    from ctdmate.rag.glossary_rag import GlossaryRAGTool
    from ctdmate.rag.term_normalizer import TermNormalizer
    from ctdmate.tools.yaml_lint import lint_yaml as _lint_yaml
except Exception:
    from ..rag.mfds_rag import MFDSRAGTool  # type: ignore
    from ..rag.glossary_rag import GlossaryRAGTool  # type: ignore
    from ..rag.term_normalizer import TermNormalizer  # type: ignore
    from .yaml_lint import lint_yaml as _lint_yaml  # type: ignore

try:
    import requests
except Exception:
    requests = None  # type: ignore

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _clip(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n] + "..."

def _dedent(s: str) -> str:
    return re.sub(r"[ \t]+\n", "\n", s).strip()

def _ensure_yaml_fence(s: str) -> str:
    if re.search(r"^```yaml", s, flags=re.M):
        return s
    if re.search(r"^\s*\{|\[\s*\]|\:\s", s):
        return f"```yaml\n{s.strip()}\n```"
    return s

def _normalize_section(s: str) -> str:
    s = (s or "").strip().upper()
    return s if s.startswith("M") else f"M{s}"

def _mk_references(cands: List[Dict[str, Any]], top_k: int = 6) -> List[Dict[str, Any]]:
    seen = set()
    refs: List[Dict[str, Any]] = []
    for r in sorted(cands or [], key=lambda x: x.get("score", 0.0), reverse=True):
        md = r.get("metadata", {}) or {}
        key = (md.get("source"), md.get("page"))
        if key in seen:
            continue
        seen.add(key)
        refs.append({
            "doc": md.get("source", "N/A"),
            "section": md.get("module", "N/A"),
            "page": md.get("page", "N/A"),
            "para_id": md.get("para_id", None),
            "snippet": _clip((r.get("content") or "").strip(), 300)
        })
        if len(refs) >= top_k:
            break
    return refs

def _cit_density(text: str) -> float:
    n = len(re.findall(r"\[CIT-\d+\]", text or ""))
    toks = max(1, len(text or "") // 4)
    return min(1.0, n / max(1, toks / 200))  # 200토큰당 인용 1개 기준

def _count_major(findings: List[Any]) -> int:
    c = 0
    for f in findings or []:
        reason = ""
        if isinstance(f, dict):
            reason = str(f.get("reason", ""))
        else:
            reason = str(getattr(f, "reason", ""))
        r = reason.lower()
        if "critical" in r or "major" in r:
            c += 1
    return c

class SolarGenerator:
    def __init__(
        self,
        enable_rag: bool = True,
        auto_normalize: bool = True,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_refs: int = 6,
        output_format: str = "yaml",
        language: str = "ko"
    ):
        self.enable_rag = enable_rag
        self.auto_normalize = auto_normalize
        self.model = model or CFG.UPSTAGE_MODEL
        self.temperature = float(temperature)
        self.max_refs = int(max_refs)
        self.output_format = output_format
        self.language = language

        self.mfds_rag: Optional[MFDSRAGTool] = None
        self.glossary: Optional[GlossaryRAGTool] = None
        self.normalizer: Optional[TermNormalizer] = None

        if enable_rag:
            try:
                self.mfds_rag = MFDSRAGTool()
                self.glossary = GlossaryRAGTool()
            except Exception:
                self.mfds_rag = None
                self.glossary = None
                self.enable_rag = False

        if auto_normalize:
            try:
                self.normalizer = TermNormalizer()
            except Exception:
                self.normalizer = None

    # --------- Upstage Chat ----------
    def _solar_chat(self, messages: List[Dict[str, str]]) -> str:
        if requests is None:
            raise RuntimeError("requests not installed. pip install requests")
        api_key = CFG.UPSTAGE_API_KEY
        if not api_key:
            raise RuntimeError("UPSTAGE_API_KEY is not set")

        base = CFG.UPSTAGE_API_BASE.rstrip("/")
        paths = [CFG.UPSTAGE_CHAT_PATH, "/solar/chat/completions"]
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages, "temperature": self.temperature, "stream": False}

        last_err = None
        for p in paths:
            try:
                url = f"{base}{p}"
                resp = requests.post(url, headers=headers, json=payload, timeout=90)
                if resp.status_code == 404:
                    last_err = f"404 at {p}"
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                last_err = str(e)
                continue
        raise RuntimeError(f"Solar chat API failed: {last_err}")

    # --------- RAG ----------
    def _retrieve(self, section: str, query: str, k: int = 6) -> List[Dict[str, Any]]:
        if not (self.enable_rag and self.mfds_rag):
            return []
        section = _normalize_section(section)
        try:
            prim = self.mfds_rag.search_by_module(query=query[:500], module=section, k=max(3, k // 2))
        except Exception:
            prim = []
        try:
            mmr = self.mfds_rag.search_with_mmr(query=query[:500], k=max(3, k - len(prim)), fetch_k=12, lambda_mult=0.5)
        except Exception:
            mmr = []
        seen = set()
        merged: List[Dict[str, Any]] = []
        for r in (prim + mmr):
            md = r.get("metadata", {}) or {}
            key = (md.get("source"), md.get("page"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(r)
            if len(merged) >= k:
                break
        return merged

    # --------- 메시지 빌드 ----------
    def _build_messages(self, section: str, user_prompt: str, ctx_docs: List[Dict[str, Any]], want_yaml: bool) -> List[Dict[str, str]]:
        sec = _normalize_section(section)
        refs = _mk_references(ctx_docs, top_k=self.max_refs)
        ctx_texts = []
        for i, r in enumerate(refs, 1):
            ctx_texts.append(f"[CIT-{i}] doc={r['doc']} section={r['section']} page={r['page']}\nSNIPPET: {r['snippet']}")
        ctx_blob = "\n\n".join(ctx_texts) if ctx_texts else "N/A"
        out_style = "YAML" if want_yaml else "Markdown"

        sys = _dedent(f"""
        역할: 제약 인허가 문서 CTD {sec} 초안 작성 에이전트.
        원칙:
        - 아래 Context 안에서만 사실을 인용. 근거 없는 추정 금지.
        - 문장 말미에 관련 근거를 대괄호 표기: [CIT-1], [CIT-2] 등.
        - 출력은 {out_style} 한 가지 형식만 사용.
        - 규제 언어. 한국어({self.language}) 유지.
        - 불명확한 값은 NEED_INPUT.
        """).strip()

        # 필수 키 힌트(간단형)
        skel_hint = json.dumps({"References": []}, ensure_ascii=False)

        inst_yaml = _dedent(f"""
        1) CTD {sec} 스켈레톤을 준수해 YAML 생성.
        2) 각 핵심 문장에 [CIT-i] 인용 표기.
        3) 최하단에 References: - {{doc, section, page, para_id}} 리스트 포함.
        4) 값이 불명확하면 "NEED_INPUT".
        5) YAML 코드펜스로 감쌈.
        스켈레톤 힌트:
        {skel_hint}
        """).strip()

        inst_md = _dedent(f"""
        1) CTD {sec} 섹션을 Markdown으로 서술.
        2) 각 핵심 문장에 [CIT-i] 인용 표기.
        3) 문서 끝에 '## References' 섹션과 - doc | section | page | para_id 목록.
        4) 불명확한 값은 NEED_INPUT.
        """).strip()

        instruction = inst_yaml if want_yaml else inst_md
        user = _dedent(f"""
        사용자 요청:
        {user_prompt.strip()}

        Context(인용 원문):
        {ctx_blob}
        """).strip()

        return [
            {"role": "system", "content": sys},
            {"role": "user", "content": instruction},
            {"role": "user", "content": user},
        ]

    # --------- 생성 ----------
    def generate(self, section: str, prompt: str, output_format: Optional[str] = None, csv_present: Optional[Any] = None) -> Dict[str, Any]:
        section = _normalize_section(section)
        want_yaml = (output_format or self.output_format).lower() == "yaml"

        ctx = self._retrieve(section, prompt, k=self.max_refs)

        offline_reason = None
        try:
            msgs = self._build_messages(section, prompt, ctx, want_yaml=want_yaml)
            text = self._solar_chat(msgs)
        except Exception as e:
            offline_reason = str(e)
            if want_yaml:
                import yaml
                text = "```yaml\n" + yaml.safe_dump({"NEED_INPUT": True, "References": []}, allow_unicode=True, sort_keys=False) + "\n```"
            else:
                text = f"### {section} Draft\n\n- NEED_INPUT\n\n## References\n- (none)"

        text = text.strip()

        # 용어 정규화
        if self.auto_normalize and self.normalizer:
            try:
                core = re.sub(r"^```yaml|```$", "", text, flags=re.M).strip() if want_yaml else text
                text_core = self.normalizer.normalize(core)
                text = _ensure_yaml_fence(text_core) if want_yaml else text_core
            except Exception:
                pass

        # Lint(YAML)
        lint_ok, findings = True, []
        body_for_cit = text
        if want_yaml:
            body = re.sub(r"^```yaml|```$", "", text, flags=re.M).strip()
            lint_ok, findings = _lint_yaml(body, section=section, csv_present=csv_present, checklist_path=CFG.CHECKLIST_PATH)
            body_for_cit = body

        # 생성 지표
        cit = _cit_density(body_for_cit)
        major_cnt = _count_major(findings)
        gen_score = 0.6 * cit + 0.4 * int(lint_ok and major_cnt <= CFG.LINT_MAX_MAJOR)
        ready = (gen_score >= CFG.GENERATE_READY_MIN) and (major_cnt <= CFG.LINT_MAX_MAJOR)

        # Convert Lint dataclass to dict (dataclass with slots=True needs manual conversion)
        def lint_to_dict(f):
            if hasattr(f, "key") and hasattr(f, "reason") and hasattr(f, "fix_hint"):
                return {"key": f.key, "reason": f.reason, "fix_hint": f.fix_hint}
            elif hasattr(f, "__dict__"):
                return f.__dict__
            else:
                return f

        return {
            "section": section,
            "format": "yaml" if want_yaml else "markdown",
            "text": text,
            "rag_used": bool(ctx),
            "rag_refs": _mk_references(ctx, top_k=self.max_refs),
            "lint_ok": bool(lint_ok),
            "lint_findings": [lint_to_dict(f) for f in findings],
            "gen_metrics": {
                "cit_density": cit,
                "lint_major": major_cnt,
                "gen_score": gen_score,
                "thresholds": {
                    "generate_ready_min": CFG.GENERATE_READY_MIN,
                    "lint_max_major": CFG.LINT_MAX_MAJOR,
                },
            },
            "ready": bool(ready),
            "offline_fallback": offline_reason,
            "created_at": _now_iso(),
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CTD 섹션 생성기(Solar Pro2 + 인용형 RAG)")
    parser.add_argument("--section", "-s", required=True, help="예: M2.3, M2.6, M2.7")
    parser.add_argument("--prompt", "-p", required=True, help="프롬프트 텍스트 또는 파일 경로")
    parser.add_argument("--format", "-f", default="yaml", choices=["yaml", "markdown"])
    parser.add_argument("--max-refs", type=int, default=6)
    parser.add_argument("--temp", type=float, default=0.2)
    parser.add_argument("--out", help="결과 저장 경로(.md/.yaml). 미지정 시 stdout")
    parser.add_argument("--no-rag", action="store_true", help="RAG 비활성")
    parser.add_argument("--no-normalize", action="store_true", help="용어 정규화 비활성")
    args = parser.parse_args()

    def _read_text(p: str | None) -> str:
        if not p: return ""
        path = Path(p)
        return path.read_text(encoding="utf-8") if path.exists() else p

    def _write_out(s: str, out: Optional[str]) -> Optional[str]:
        if not out:
            print(s); return None
        op = Path(out); op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(s, encoding="utf-8"); return str(op)

    gen = SolarGenerator(
        enable_rag=not args.no_rag,
        auto_normalize=not args.no_normalize,
        temperature=args.temp,
        max_refs=args.max_refs,
        output_format=args.format,
    )

    req = _read_text(args.prompt)
    out = gen.generate(section=args.section, prompt=req, output_format=args.format)
    _write_out(out["text"], args.out)
    meta = {k: v for k, v in out.items() if k not in ("text",)}
    print("\n---\nMETA:\n" + json.dumps(meta, ensure_ascii=False, indent=2))

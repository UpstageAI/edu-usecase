# ctdmate/tools/gen_rag.py
"""
ToolX: gen_rag.py — RAG 컨텍스트 생성기
목적
- 질의(query)와 섹션(module)을 입력받아 MFDS/ICH 컬렉션에서 상위 스니펫을 수집
- [CIT-i] 라벨이 달린 콘텍스트 블록(Markdown) 또는 JSON 메타를 출력/저장
- 파이프라인/프롬프트 디버깅용 유틸

사용
  python -m ctdmate.tools.gen_rag -s M2.6 -q "독성시험 요약 표 작성 규칙" -k 8 -o ctx.md
  python -m ctdmate.tools.gen_rag -s M2.7 -q prompt.txt --format json

출력
- format=md  : [CIT-i] doc=... section=... page=... + SNIPPET 블록
- format=json: {"refs":[{doc,section,page,snippet,score}], "ctx_md":"..."}
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import re

# config / RAG
try:
    from ctdmate.app import config as CFG
except Exception:
    from ..app import config as CFG  # type: ignore

try:
    from ctdmate.rag.mfds_rag import MFDSRAGTool
except Exception:
    from ..rag.mfds_rag import MFDSRAGTool  # type: ignore


def _normalize_section(s: str) -> str:
    s = (s or "").strip().upper()
    return s if s.startswith("M") else f"M{s}"

def _clip(s: str, n: int = 300) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + "..."

def _mk_references(cands: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
    seen = set()
    refs: List[Dict[str, Any]] = []
    for r in sorted(cands or [], key=lambda x: float(x.get("score", 0.0)), reverse=True):
        md = r.get("metadata", {}) or {}
        key = (md.get("source"), md.get("page"))
        if key in seen:
            continue
        seen.add(key)
        refs.append({
            "doc": md.get("source", "N/A"),
            "section": md.get("module", "N/A"),
            "page": md.get("page", "N/A"),
            "para_id": md.get("para_id"),
            "snippet": _clip((r.get("content") or "")),
            "score": float(r.get("score", 0.0)),
        })
        if len(refs) >= top_k:
            break
    return refs

def _render_ctx_md(refs: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for i, r in enumerate(refs, 1):
        lines.append(f"[CIT-{i}] doc={r['doc']} section={r['section']} page={r['page']}")
        lines.append(f"SNIPPET: {r['snippet']}\n")
    return "\n".join(lines).rstrip()

class RAGContextGenerator:
    """
    섹션+질의 → 하이브리드 검색(+선택 MMR) → 참조 리스트 + 콘텍스트 MD
    """
    def __init__(self, k: int = 8):
        self.k = int(k)
        self.tool = MFDSRAGTool()

    def build(
        self,
        section: str,
        query: str,
        k: Optional[int] = None,
        use_mmr: bool = False,
        fetch_k: int = 30,
        lambda_mult: float = 0.5,
    ) -> Dict[str, Any]:
        sec = _normalize_section(section)
        kk = int(k or self.k)

        if use_mmr:
            cands = self.tool.search_with_mmr(
                query=query, k=kk, fetch_k=max(fetch_k, kk * 4), lambda_mult=lambda_mult, module=sec
            )
        else:
            cands = self.tool.search_by_module(query=query, module=sec, k=kk)

        refs = _mk_references(cands, top_k=kk)
        ctx_md = _render_ctx_md(refs)
        return {
            "section": sec,
            "k": kk,
            "mmr": bool(use_mmr),
            "refs": refs,
            "ctx_md": ctx_md,
        }

# -------- CLI --------
def _read_text(p: str) -> str:
    path = Path(p)
    return path.read_text(encoding="utf-8") if path.exists() else p

def _write_text(s: str, out: Optional[str]) -> Optional[str]:
    if not out:
        print(s)
        return None
    op = Path(out); op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(s, encoding="utf-8")
    return str(op)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="RAG 컨텍스트 생성기(MFDS/ICH)")
    ap.add_argument("-s", "--section", required=True, help="예: M2.3, M2.6, M2.7")
    ap.add_argument("-q", "--query", required=True, help="질의 텍스트 또는 파일 경로")
    ap.add_argument("-k", "--topk", type=int, default=8)
    ap.add_argument("--mmr", action="store_true", help="MMR 다양성 재랭크 사용")
    ap.add_argument("--fetch-k", type=int, default=30)
    ap.add_argument("--lambda-mult", type=float, default=0.5)
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("-o", "--out", help="저장 경로(.md/.json). 미지정 시 stdout")
    args = ap.parse_args()

    q = _read_text(args.query)
    gen = RAGContextGenerator(k=args.topk)
    res = gen.build(
        section=args.section,
        query=q,
        k=args.topk,
        use_mmr=args.mmr,
        fetch_k=args.fetch_k,
        lambda_mult=args.lambda_mult,
    )

    if args.format == "md":
        out_s = res["ctx_md"]
        _write_text(out_s, args.out)
    else:
        _write_text(json.dumps(res, ensure_ascii=False, indent=2), args.out)

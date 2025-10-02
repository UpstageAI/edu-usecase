# ctdmate/tools/xai_trace.py
"""
XAITrace: 생성/검증 과정 추적 로그(JSON/JSONL)

용도
- RAG 검색 스니펫, 임계값, 판정 근거 저장
- 파이프라인(Router→Parse→Validate→Generate) 각 단계 이벤트 기록
- 아티팩트 경로(MD/JSONL/출력물)와 해시를 함께 보존

사용
    from ctdmate.tools.xai_trace import XAITrace

    xt = XAITrace(component="gen_solar", meta={"section":"M2.6"})
    xt.event("router.plan", plan)
    xt.event("rag.refs", xt.compact_refs(rag_refs))
    xt.metrics({"coverage":0.72, "rag_conf":0.43, "score":0.68})
    xt.output(text=gen_text, artifacts=[out_path])
    path = xt.save()  # ./out/xai/<run_id>.json
"""
from __future__ import annotations
import os, json, time, hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterable


# ----------------- 유틸 -----------------
def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256(s: str | bytes) -> str:
    h = hashlib.sha256()
    h.update(s if isinstance(s, bytes) else s.encode("utf-8"))
    return h.hexdigest()

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _path_or_none(x: Any) -> Optional[str]:
    try:
        return str(Path(x))
    except Exception:
        return None


# ----------------- 본체 -----------------
class XAITrace:
    """
    단일 실행(run) 추적기.
    - component: "router" | "smartdoc" | "reg_rag" | "gen_solar" | 기타
    - events: 시계열 로그
    - metrics: 수치 근거(임계값, 점수 등)
    - output: 생성물(텍스트 미리보기 + 파일 경로)
    """

    def __init__(
        self,
        component: str,
        session_id: Optional[str] = None,
        out_dir: str = "./out/xai",
        run_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ):
        self.component = component
        self.session_id = session_id or _sha256(str(time.time()))[:8]
        self.run_id = run_id or _sha256(f"{self.session_id}:{component}:{time.time()}")[:16]
        self.out_dir = Path(out_dir)
        _ensure_dir(self.out_dir)

        self.meta: Dict[str, Any] = meta or {}
        self.events: List[Dict[str, Any]] = []
        self._metrics: Dict[str, Any] = {}
        self._output: Dict[str, Any] = {}

        self.started_at = _now_iso()

    # ---------- 이벤트 ----------
    def event(self, kind: str, data: Any, *, ts: Optional[str] = None) -> None:
        self.events.append({
            "ts": ts or _now_iso(),
            "kind": kind,
            "data": data,
        })

    # ---------- 메트릭 ----------
    def metrics(self, d: Dict[str, Any]) -> None:
        self._metrics.update(d or {})

    # ---------- 인용/스니펫 압축 ----------
    @staticmethod
    def compact_refs(refs: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        seen = set()
        for r in refs or []:
            md = r.get("metadata") or {}
            # 두 포맷 모두 허용(refs 또는 retriever 문서)
            doc = r.get("doc") or md.get("source") or "N/A"
            sec = r.get("section") or md.get("module") or "N/A"
            page = r.get("page") or md.get("page")
            key = (doc, page)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "doc": doc,
                "section": sec,
                "page": page,
                "score": float(r.get("score", 0.0)),
                "snippet": (r.get("snippet") or r.get("content") or "")[:300] + "...",
            })
        return out

    # ---------- 출력 ----------
    def output(
        self,
        *,
        text: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
        store_text_file: bool = False,
        text_filename: Optional[str] = None,
    ) -> None:
        preview = None
        text_path = None
        if text:
            preview = text[:1000] + ("..." if len(text) > 1000 else "")
            if store_text_file:
                fname = text_filename or f"{self.run_id}.out.txt"
                tp = self.out_dir / fname
                tp.write_text(text, encoding="utf-8")
                text_path = str(tp)

        arts: List[Dict[str, Any]] = []
        for a in artifacts or []:
            p = _path_or_none(a)
            if not p:
                continue
            try:
                size = Path(p).stat().st_size
            except Exception:
                size = None
            arts.append({"path": p, "size": size, "sha256": _sha256(p)})

        self._output = {"preview": preview, "text_path": text_path, "artifacts": arts}

    # ---------- 저장 ----------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "component": self.component,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": _now_iso(),
            "meta": self.meta,
            "events": self.events,
            "metrics": self._metrics,
            "output": self._output,
        }

    def save(self, *, jsonl: bool = False) -> str:
        obj = self.to_dict()
        if jsonl:
            path = self.out_dir / f"{self.run_id}.jsonl"
            with path.open("w", encoding="utf-8") as f:
                for ev in obj["events"]:
                    f.write(json.dumps({"run_id": self.run_id, **ev}, ensure_ascii=False) + "\n")
            return str(path)

        path = self.out_dir / f"{self.run_id}.json"
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)


# ----------------- 편의 컨텍스트 -----------------
class trace_run:
    """
    with trace_run("gen_solar", meta={"section":"M2.6"}) as xt:
        xt.event("router.plan", plan)
        ...
    path = xt.save()
    """
    def __init__(self, component: str, **kw):
        self.xt = XAITrace(component=component, **kw)
    def __enter__(self) -> XAITrace:
        return self.xt
    def __exit__(self, exc_type, exc, tb):
        # 자동 저장은 하지 않음. 호출측에서 save() 호출.
        return False

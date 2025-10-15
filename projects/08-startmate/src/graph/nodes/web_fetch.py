# src/graph/nodes/web_fetch.py
from __future__ import annotations
import os, re, html, requests
from core.utils import Timer
from core.schemas import State

UA = "Mozilla/5.0 (compatible; PatentRAG/1.0)"

def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    # 제거 우선: script/style
    raw = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    raw = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", raw)
    # 태그 제거
    txt = re.sub(r"(?s)<[^>]+>", " ", raw)
    # HTML 엔티티 해제 & 공백 정리
    txt = html.unescape(txt)
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

def node_web_fetch(state: State) -> State:
    hits = state.hits or []
    top = int(os.getenv("WEB_FETCH_TOP", "3"))
    per_page = int(os.getenv("WEB_PAGE_CHAR_BUDGET", "4000"))
    total_budget = int(os.getenv("WEB_CTX_CHAR_BUDGET", "12000"))

    urls = [h.url for h in hits[:top] if h.url]
    fetched_meta = []
    chunks = []

    with Timer() as t:
        for u in urls:
            try:
                r = requests.get(u, headers={"User-Agent": UA}, timeout=(10, 30))
                status = r.status_code
                text = ""
                if status == 200:
                    clean = _strip_html(r.text)
                    if len(clean) > per_page:
                        clean = clean[:per_page]
                    chunks.append(f"[WEB] {u}\n{clean}")
                fetched_meta.append({"url": u, "status": status, "chars": len(text)})
            except Exception as e:
                fetched_meta.append({"url": u, "status": -1, "error": str(e)})

    # 컨텍스트 예산 내로 머지
    prev = (state.ctx or "")
    joined = "\n\n".join(chunks)
    remain = max(0, total_budget - len(prev))
    merged = (prev + ("\n\n" if prev and joined else "") + joined[:remain]).strip()

    # 결과 반영
    state.ctx = merged

    timings = dict(getattr(state, "timings", {}) or {})
    timings["web_ms"] = t.ms
    state.timings = timings

    dbg = dict(getattr(state, "debug", {}) or {})
    dbg["web_fetch"] = {
        "requested": urls,
        "pages_used": len(chunks),
        "per_page_budget": per_page,
        "total_budget": total_budget,
        "ctx_len_after": len(state.ctx or ""),
        "fetched": [{"url": f.get("url"), "status": f.get("status", -1)} for f in fetched_meta],
    }
    state.debug = dbg
    return state

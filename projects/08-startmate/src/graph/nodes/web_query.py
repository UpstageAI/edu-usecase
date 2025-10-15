from __future__ import annotations
import os, requests
from core.utils import Timer
from core.schemas import State, SearchHit

API = os.getenv("SEARCH_API", "tavily").lower()
TAVILY_URL = os.getenv("TAVILY_URL", "https://api.tavily.com/search")
TAVILY_KEY = os.getenv("TAVILY_API_KEY", "")

def _tavily_search(query: str, n: int = 5, depth: str = "basic") -> list[SearchHit]:
    if not TAVILY_KEY:
        raise RuntimeError("missing TAVILY_API_KEY")
    payload = {
        "api_key": TAVILY_KEY,
        "query": query,
        "max_results": n,
        "search_depth": depth,   # "basic" | "advanced"
        # "include_answer": False, "include_images": False, ...
    }
    r = requests.post(TAVILY_URL, json=payload, timeout=(10, 30))
    r.raise_for_status()
    data = r.json()
    out: list[SearchHit] = []
    for it in data.get("results", []):
        out.append(SearchHit(
            title=it.get("title") or it.get("url") or "",
            url=it.get("url") or "",
            snippet=(it.get("content") or "")[:400],
        ))
    return out

def node_web_query(state: State) -> State:
    q = state.query or ""
    n = int(os.getenv("WEB_RESULTS", "5"))
    depth = os.getenv("WEB_DEPTH", "basic")

    with Timer() as t:
        try:
            if API == "tavily":
                hits = _tavily_search(q, n=n, depth=depth)
            else:
                raise RuntimeError(f"unknown SEARCH_API={API}")
        except Exception as e:
            dbg = dict(getattr(state, "debug", {}) or {})
            dbg["web_query_error"] = str(e)
            state.debug = dbg
            state.hits = []
            return state

    state.hits = hits
    timings = dict(getattr(state, "timings", {}) or {})
    timings["webq_ms"] = t.ms
    state.timings = timings

    dbg = dict(getattr(state, "debug", {}) or {})
    dbg["web_query"] = {
        "provider": API, "query": q, "max_results": n, "depth": depth,
        "hits": len(hits),
        "top": [{"title": h.title, "url": h.url} for h in hits[:5]],
    }
    state.debug = dbg
    return state

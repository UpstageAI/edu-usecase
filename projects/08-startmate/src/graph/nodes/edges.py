# graph/nodes/edges.py
from __future__ import annotations
from core.debug import log, set_field
from core.schemas import State

def web_to_retrieve_edge(state: State) -> State:
    """웹 요약을 바탕으로 RAG 검색 질의를 보강(간단 버전)."""
    sumtxt = getattr(state, "web_summary", "") or ""
    q = getattr(state, "query", "") or ""
    if sumtxt:
        boosted = q + " " + " ".join(sumtxt.split()[:20])
        set_field(state, "query", boosted)
        log("web.edge", boosted_query_len=len(boosted))
    return state

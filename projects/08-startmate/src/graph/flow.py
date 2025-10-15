# src/graph/flow.py
from __future__ import annotations

from types import SimpleNamespace

from core.schemas import State
from .nodes.route import node_route, choose_branch
from .nodes.retrieve import node_retrieve_embed, node_retrieve_ctx
from .nodes.answer import node_answer
from .nodes.web_query import node_web_query
from .nodes.web_fetch import node_web_fetch
from .nodes.web_summary import node_web_summarize
from .nodes.edges import web_to_retrieve_edge


def build_graph():
    """
    Orchestrates the pipeline as a simple callable graph.

    Returns
    -------
    SimpleNamespace
        - invoke(state: State) -> State
        - nodes: dict[str, callable]  (for debugging/inspection)
    """
    nodes = {
        "route": node_route,
        "retrieve_embed": node_retrieve_embed,
        "retrieve_ctx": node_retrieve_ctx,
        "answer": node_answer,
        "web_query": node_web_query,
        "web_fetch": node_web_fetch,
        "web_summarize": node_web_summarize,
        "web_to_retrieve_edge": web_to_retrieve_edge,
    }

    # ---------------- helpers ---------------- #

    def _looks_like_state(x) -> bool:
        # Pydantic State 인스턴스이거나, 최소한 query 속성이 있으면 state로 간주
        if isinstance(x, State):
            return True
        try:
            return getattr(x, "query", None) is not None
        except Exception:
            return False

    def _call_node(step, s: State) -> State:
        """노드 호출. 반환이 None/스칼라면 기존 state 유지."""
        if step is None:
            return s
        out = step(s)
        if out is None:
            return s
        return out if _looks_like_state(out) else s

    def _no_docs(s: State) -> bool:
        docs = getattr(s, "docs", None)
        return not docs or len(docs) == 0

    # ---------------- runner ----------------- #

    def run(state: State) -> State:
        s = state  # 그대로 유지 (dict로 변환 X)

        # 1) 라우팅: node_route는 state.route를 세팅하고 디버그/타이밍을 남김
        s = _call_node(node_route, s)

        # 2) 분기 결정: 규칙(요약/최신) 우선 → LLM 신뢰도 → 기본 retrieve
        try:
            br = (choose_branch(s) or "retrieve").lower()
        except Exception:
            br = "retrieve"

        # 디버그에 브랜치 기록(노드에서도 기록하지만 여기서도 보강)
        try:
            dbg = dict(getattr(s, "debug", {}) or {})
            dbg["branch"] = br
            s.debug = dbg
        except Exception:
            pass

        # 3) 브랜치 실행
        if br == "web":
            # 웹 검색 → 페치 → 요약 → (필요시) RAG 연계 → 답변
            s = _call_node(node_web_query, s)
            s = _call_node(node_web_fetch, s)
            s = _call_node(node_web_summarize, s)
            s = _call_node(web_to_retrieve_edge, s)   # 요약을 기반으로 질의 보강
            s = _call_node(node_retrieve_embed, s)
            s = _call_node(node_retrieve_ctx, s)
            s = _call_node(node_answer, s)

        elif br == "answer":
            # 바로 답변(히스토리/기존 ctx 활용)
            s = _call_node(node_answer, s)

        elif br == "summarize":
            # 요약 의도 명확 → 히스토리 중심으로 answer에서 처리
            s = _call_node(node_answer, s)

        else:  # 'retrieve' (기본)
            s = _call_node(node_retrieve_embed, s)
            s = _call_node(node_retrieve_ctx, s)
            if _no_docs(s):
                # RAG 결과가 비면 웹으로 폴백해 항상 답이 나오도록
                print("[router] 0 docs -> fallback to web")
                s = _call_node(node_web_query, s)
                s = _call_node(node_web_fetch, s)
                s = _call_node(node_web_summarize, s)
                # 웹 요약만으로도 답변 가능하지만, 문서가 생겼다면 answer가 함께 활용
                s = _call_node(node_answer, s)
            else:
                s = _call_node(node_answer, s)

        return s

    return SimpleNamespace(
        invoke=run,
        nodes=nodes,
    )

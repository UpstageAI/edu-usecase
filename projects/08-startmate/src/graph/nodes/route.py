from core.utils import Timer
from core.schemas import State, Route
from core.router_client import RouterClient

_router = RouterClient()

def _choose_branch(query: str, route: Route | None) -> str:
    q = (query or "").lower()
    if any(k in q for k in ("요약", "정리", "회의록", "핵심만")): return "summarize"
    if any(k in q for k in ("최근","최신","시장","동향","올해","이번 분기","신규","뉴스","지난주")): return "web"
    if route and route.confidence >= 0.5: return route.tool
    return "retrieve"

def node_route(state: State) -> State:
    with Timer() as t:
        out = _router.classify_with_debug(state.query)
        state.route = Route(tool=out["tool"], confidence=out["confidence"], extra=out["extra"])
        state.debug["router"] = out["_debug"]
        state.debug["branch"] = _choose_branch(state.query, state.route)
    state.timings["route_ms"] = t.ms
    return state

def choose_branch(state: State) -> str:
    return state.debug.get("branch") or _choose_branch(state.query, state.route)

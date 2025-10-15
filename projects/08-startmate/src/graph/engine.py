"""
A tiny, framework-free graph runner with branching, suitable for multi-turn tests.
- Keeps your existing node functions intact.
- Exposes `GraphRunner.invoke(state)` like LangGraph for easy drop-in.
"""
from __future__ import annotations

from typing import Callable, Dict
from .nodes.route import node_route, choose_branch
from .nodes.retrieve import node_retrieve_embed
from .nodes.context import node_retrieve_ctx
from .nodes.answer import node_answer
from .nodes.web_query import node_web_query
from .nodes.web_fetch import node_web_fetch
from .nodes.web_summary import node_web_summarize
from .nodes.summarize import node_summarize_thread
from .nodes.edges import web_to_retrieve_edge
from ..core.schemas import State


class GraphRunner:
    """Minimal orchestrator implementing the intended pipeline:

    route -> branch:
      - retrieve: retrieve_embed -> retrieve_ctx -> answer
      - web:      web_query -> web_fetch -> (edge) -> [retrieve_embed]? -> web_summarize
      - summarize: summarize_thread
    """

    def __init__(self):
        # registry (optional, useful for debug/inspection)
        self.nodes: Dict[str, Callable[[State], State]] = {
            "route": node_route,
            "retrieve_embed": node_retrieve_embed,
            "retrieve_ctx": node_retrieve_ctx,
            "answer": node_answer,
            "web_query": node_web_query,
            "web_fetch": node_web_fetch,
            "web_summarize": node_web_summarize,
            "summarize_thread": node_summarize_thread,
        }

    def invoke(self, state: State) -> State:
        # 1) route
        state = self.nodes["route"](state)
        branch = choose_branch(state)

        if branch == "web":
            # 2) web branch
            state = self.nodes["web_query"](state)
            state = self.nodes["web_fetch"](state)
            # Optional transition to retrieve if patents/KIPO URL detected
            next_hop = web_to_retrieve_edge(state)
            if next_hop == "retrieve_embed":
                state = self.nodes["retrieve_embed"](state)
                # Optional: when web led to specific internal docs, we can answer from internal ctx instead
                # but here we continue with a web summary for consistency
            state = self.nodes["web_summarize"](state)
            return state

        if branch == "summarize":
            # 2) summarize branch (multi-turn aware via state.history)
            state = self.nodes["summarize_thread"](state)
            return state

        # default: retrieve branch
        state = self.nodes["retrieve_embed"](state)
        state = self.nodes["retrieve_ctx"](state)
        state = self.nodes["answer"](state)
        return state

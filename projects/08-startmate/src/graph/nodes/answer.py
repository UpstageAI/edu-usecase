# src/graph/nodes/answer.py
from __future__ import annotations
import os
from core.utils import Timer
from core.llm_client import LLMClient
from core.schemas import State

_llm = LLMClient()

def _history_to_text(history: list[dict], max_turns: int = 12, max_chars: int = 4000) -> str:
    if not history:
        return ""
    parts = []
    for m in history[-max_turns:]:
        role = m.get("role") or ""
        content = (m.get("content") or "").strip()
        if not content:
            continue
        tag = "User" if role == "user" else "Assistant" if role == "assistant" else role
        parts.append(f"{tag}: {content}")
    txt = "\n".join(parts)
    return txt[:max_chars]

def node_answer(state: State) -> State:
    with Timer() as t:
        # 1) 컨텍스트 구성(우선순위: state.ctx → docs → history)
        ctx = state.ctx
        if not ctx and state.docs:
            ctx = "\n\n".join(
                f"[{(d.title or d.id or '')}] (score={d.score:.4f})\n{(d.text or '').strip()}"
                for d in state.docs[:6]
                if (d.text or "").strip()
            )
        if not ctx:
            ctx = _history_to_text(state.history)

        # 2) 최종 컨텍스트 안전 여유
        budget = int(os.getenv("CTX_BUDGET_CHARS", "15000"))
        ctx = (ctx or "")
        if len(ctx) > budget:
            ctx = ctx[:budget]

        system = (
            "당신은 특허/법률/검색 보조 AI입니다. 주어진 컨텍스트만 근거로 답하세요. "
            "불확실하면 부족하다고 명시하세요. 각 주요 결론에는 [#1],[#2] 식 라벨을 부여하세요."
        )
        user = state.query or ""
        prompt = (
            f"<|system|>{system}</|system|>\n"
            f"<|user|>{user}</|user|>\n"
            f"<|assistant|>컨텍스트:\n{ctx}\n\n최종 답변:"
        )

        state.answer = _llm.generate_text(prompt, max_tokens=700).strip()

        # 인용 & 디버그
        state.citations = [d.meta.get("url", "") for d in (state.docs or []) if d.meta.get("url")]
        dbg = dict(getattr(state, "debug", {}) or {})
        dbg["answer"] = {
            "ctx_len_used": len(ctx),
            "citations_n": len(state.citations),
        }
        state.debug = dbg

    state.timings["answer_ms"] = t.ms
    return state

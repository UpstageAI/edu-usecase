# graph/nodes/web_summary.py
from __future__ import annotations
from core.utils import Timer
from core.llm_client import LLMClient
from core.debug import log, set_field
from core.schemas import State

_llm = LLMClient()

def _build_sum_prompt(query: str, docs: list[dict]) -> str:
    parts = []
    for i, d in enumerate(docs[:5], start=1):
        parts.append(f"[{i}] {d.get('title','(무제)')} - {d.get('url','')}\n{d.get('text','')[:2000]}")
    corpus = "\n\n".join(parts)
    return (
        "다음 웹 문서들을 근거로 질문에 대한 핵심 요약을 bullet로 작성하고, "
        "각 bullet 끝에 [#n] 형태로 출처 인덱스를 붙여주세요.\n\n"
        f"질문:\n{query}\n\n문서:\n{corpus}\n\n요약:"
    )

def node_web_summarize(state: State) -> State:
    with Timer() as t:
        q = getattr(state, "query", "") or ""
        docs = getattr(state, "web_pages", []) or []
        prompt = _build_sum_prompt(q, docs)
        summary = _llm.generate_text(prompt, max_tokens=400).strip()

        set_field(state, "web_summary", summary)
        try: state.timings["websum_ms"] = t.ms
        except Exception: pass

    log("web.sum", used_docs=min(5, len(docs)), prompt_chars=len(prompt), summary_chars=len(summary), ms=t.ms)
    return state

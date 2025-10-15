from core.utils import Timer
from core.llm_client import LLMClient
from core.schemas import State

_llm = LLMClient()

def node_retrieve_ctx(state: State) -> State:
    with Timer() as t:
        bullets = "\n".join(f"- {getattr(d, 'text', '')[:500]}" for d in state.docs[:6])
        prompt = f"""<|system|>다음 근거를 중복 없이 핵심만 남기도록 압축하세요. 출처 구분을 위해 항목 순서를 유지하세요.</|system|>
        <|user|>근거:\n{bullets}</|user|>
        <|assistant|>압축:"""
        state.ctx = _llm.generate_text(prompt, max_tokens=700).strip()
    state.timings["ctx_ms"] = t.ms
    return state
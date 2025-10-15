from core.utils import Timer
from core.llm_client import LLMClient
from core.schemas import State

_llm = LLMClient()


def node_summarize_thread(state: State) -> State:
    """최근 대화 맥락(멀티턴) + 현재 질의를 반영해 요약을 생성."""
    with Timer() as t:
        hist = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in state.history[-20:])
        prompt = f"""<|system|>대화 요약가입니다. 의도/결정/액션아이템/미해결을 구조적으로 요약하세요. 최신 사용자 질문의 의도를 반영하세요.</|system|>
<|user|>대화 이력:\n{hist}\n\n최신 질문:\n{state.query}</|user|>
<|assistant|>요약:"""
        state.answer = _llm.generate_text(prompt, max_tokens=600).strip()
    state.timings["summarize_ms"] = t.ms
    return state

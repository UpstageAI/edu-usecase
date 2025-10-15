from __future__ import annotations

ROUTER_SYSTEM = (
    "당신은 IP/특허 비서의 라우팅 모델입니다. 반드시 JSON만 출력합니다. "
    '키는 {"tool","confidence"} 이며 tool ∈ {"retrieve","summarize","web"} 입니다. '
    '불확실하면 tool="retrieve" 로 하세요.'
)

def router_prompt(query: str) -> str:
    return f"<|system|>{ROUTER_SYSTEM}</|system|>\n<|user|>{query}</|user|>\n<|assistant|>"

def answer_prompt(query: str, ctx: str) -> str:
    return f"""<|system|>특허/법률 도우미입니다. 아래 컨텍스트만 근거로 사실 기반으로 답변하세요.
불확실하면 부족하다고 명시하고, 각 결론엔 [#1],[#2] 형태의 근거 라벨을 붙이세요.</|system|>
<|user|>{query}</|user|>
<|assistant|>컨텍스트:
{ctx}

최종 답변:"""

def summarizer_prompt(history_str: str) -> str:
    return f"""<|system|>대화 히스토리를 요약하세요: 목표/결정/액션아이템/미해결.</|system|>
<|user|>{history_str}</|user|>
<|assistant|>요약:"""

def web_query_prompt(query: str) -> str:
    return f"""<|system|>질의를 검색에 적합한 3~5개의 키워드/구문으로 확장하세요.
최신 연도/기간이 중요하면 포함하세요. JSON 배열로만 출력.</|system|>
<|user|>{query}</|user|>
<|assistant|>"""

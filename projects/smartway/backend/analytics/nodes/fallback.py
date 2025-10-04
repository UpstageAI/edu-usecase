"""
Fallback Node

Intent 분류 실패 시 기본 응답을 제공하는 노드
"""
from analytics.types.state_types import AnalyticsState
from langchain_core.messages import AIMessage


def fallback_response(state: AnalyticsState):
    """
    Intent 분류 실패 시 기본 응답 (LangGraph Node)

    Args:
        state (AnalyticsState): 현재 그래프 상태

    Returns:
        dict: 업데이트할 상태 {"messages": [...], "analysis_result": "..."}
    """
    fallback_message = """
죄송합니다. 질문을 이해하지 못했습니다.

다음과 같은 질문을 시도해보세요:

**Find/Highlight 질문:**
- "가장 포화가 많은 노선은?"
- "운행 단가가 가장 높은 노선은?"
- "BYC 사거리는 어디야?"

**Analysis 질문:**
- "월별 운행 단가 추이를 보여줘"
- "노선별 수익률 비교해줘"
- "전체 노선 통계를 보여줘"
    """

    response = AIMessage(content=fallback_message.strip())

    print("⚠️  Fallback response activated")

    return {
        "messages": [response],
        "analysis_result": fallback_message.strip()
    }

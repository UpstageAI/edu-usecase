"""
Router Node - Intent Analysis

LLM을 사용하여 사용자 질문의 intent를 분석하고 적절한 경로로 라우팅
"""
from analytics.types.state_types import AnalyticsState
from config import build_chat_model
from langchain_core.messages import SystemMessage
import json


def intent_analyzer(state: AnalyticsState):
    """
    LLM을 사용하여 사용자 질문의 Intent 분석 (LangGraph Node)

    Args:
        state (AnalyticsState): 현재 그래프 상태

    Returns:
        dict: 업데이트할 상태 {"intent_type": "find_highlight" | "analysis" | "fallback"}

    Intent Types:
    - find_highlight: 특정 노선/정류장을 찾거나 하이라이트하는 질문
    - analysis: 데이터 분석, 차트 생성, 통계 요청
    - fallback: 위 두 가지에 해당하지 않는 질문

    Examples:
    - "가장 포화가 많은 노선은?" → find_highlight
    - "월별 운행 단가 추이를 보여줘" → analysis
    - "안녕하세요" → fallback
    """
    # 사용자 메시지 추출
    user_message = state["messages"][-1]
    user_question = user_message.content if hasattr(user_message, 'content') else str(user_message)

    # LLM을 사용한 Intent 분류
    system_prompt = """
당신은 버스 노선 데이터 분석 시스템의 Intent Classifier입니다.

사용자 질문을 분석하여 다음 3가지 중 하나로 분류하세요:

1. **find_highlight**: 특정 노선이나 정류장을 찾거나 하이라이트하는 질문
   - 예시: "가장 포화가 많은 노선은?", "운행 단가가 가장 높은 노선은?", "BYC 사거리는 어디야?"
   - 특징: "어디", "어느", "가장", "최대", "최소", "높은", "낮은" 등의 표현 포함
   - 목적: 그래프에서 특정 edge/node를 하이라이트

2. **analysis**: 데이터 분석, 차트 생성, 통계 정보 요청
   - 예시: "월별 운행 단가 추이를 보여줘", "노선별 수익률 비교", "전체 노선 통계"
   - 특징: "분석", "추이", "비교", "그래프", "차트", "통계", "현황" 등의 표현 포함
   - 목적: 차트나 표를 생성하여 데이터 시각화

3. **fallback**: 위 두 가지에 해당하지 않는 질문
   - 예시: "안녕하세요", "도움말", "무엇을 할 수 있나요?"
   - 목적: 기본 응답 제공

응답 형식 (JSON만 출력, 다른 설명 금지):
{
    "intent": "find_highlight" | "analysis" | "fallback",
    "confidence": 0.0-1.0,
    "reason": "분류 근거 간단히 설명"
}
"""

    messages = [
        SystemMessage(content=system_prompt),
        user_message
    ]

    # LLM 호출
    llm = build_chat_model(temperature=0.3)
    response = llm.invoke(messages)

    # 응답 내용 로깅
    print(f"📝 LLM Raw Response: {response.content}")

    try:
        # JSON 파싱 (여러 형식 처리)
        content = response.content.strip()

        # ```json 블록 제거
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        result = json.loads(content)
        intent = result.get("intent", "fallback")
        confidence = result.get("confidence", 0.0)
        reason = result.get("reason", "")

        print(f"🎯 Intent Analysis (LLM): {intent} (confidence: {confidence:.2f})")
        print(f"   Reason: {reason}")

    except json.JSONDecodeError as e:
        # JSON 파싱 실패 시 fallback
        print(f"⚠️  Intent parsing failed: {str(e)}")
        print(f"   Raw content: {response.content[:200]}")
        intent = "fallback"

    return {"intent_type": intent}


def conditional_router(state: AnalyticsState) -> str:
    """
    Intent에 따라 다음 노드 결정 (LangGraph Conditional Edge)

    Args:
        state (AnalyticsState): 현재 그래프 상태

    Returns:
        str: 다음 노드 이름
    """
    intent = state.get("intent_type", "fallback")

    route_map = {
        "find_highlight": "get_graph_data",
        "analysis": "get_bus_data",
        "fallback": "fallback_response"
    }

    next_node = route_map.get(intent, "fallback_response")
    print(f"🔀 Routing to: {next_node}")

    return next_node

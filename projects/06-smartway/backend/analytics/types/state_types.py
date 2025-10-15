"""
Analytics Agent State Types

LangGraph에서 사용되는 상태(State) 타입 정의
"""
from typing import TypedDict, Annotated, Optional, Literal
from langgraph.graph.message import add_messages


class AnalyticsState(TypedDict):
    """
    Analytics Agent의 전체 상태를 정의하는 클래스

    LangGraph 실행 중 유지되는 상태:
    - messages: 대화 메시지 리스트 (자동 누적)
    - intent_type: 질문 유형 (find_highlight | analysis | fallback)

    Find/Highlight Path 상태:
    - graph_data: ReactFlow 그래프 데이터
    - highlight_edge: 선택된 엣지 정보

    Analysis Path 상태:
    - transport_data: 승하차 정보 JSON 문자열
    - commute_allowance_data: 통근 수당 JSON 문자열
    - chart_type: 차트 타입
    - chart_data: 차트 데이터
    - analysis_result: 분석 결과 텍스트
    """
    messages: Annotated[list, add_messages]
    intent_type: Optional[Literal['find_highlight', 'analysis', 'fallback']]

    # Find/Highlight specific
    graph_data: Optional[dict]
    highlight_edge: Optional[dict]

    # Analysis specific
    transport_data: Optional[str]
    commute_allowance_data: Optional[str]
    chart_type: Optional[Literal['line_chart', 'bar_chart', 'table', 'text_summary']]
    chart_data: Optional[dict]
    analysis_result: Optional[str]
    insights: Optional[list]

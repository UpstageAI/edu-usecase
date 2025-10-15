"""
Analytics API Routes

LangGraph를 실행하여 사용자 질문에 대한 분석 결과 반환
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from langchain_core.messages import HumanMessage
from analytics.graph.analytics_graph import get_analytics_graph

router = APIRouter()


class QuestionRequest(BaseModel):
    """사용자 질문 요청 모델"""
    question: str


class AnalyticsResponse(BaseModel):
    """분석 결과 응답 모델"""
    intent_type: str
    highlight_edge: Optional[Dict[str, Any]] = None
    chart_data: Optional[Dict[str, Any]] = None
    analysis_result: Optional[str] = None
    chart_type: Optional[str] = None
    insights: Optional[list] = None


@router.post("/analytics", response_model=AnalyticsResponse)
async def analyze(request: QuestionRequest):
    """
    Analytics Agent API - LangGraph 실행

    Flow:
    1. 사용자 질문을 HumanMessage로 변환
    2. LangGraph invoke로 실행
    3. 결과 state에서 응답 추출
    4. FastAPI response model로 반환

    Example:
        POST /api/analytics
        Body: {"question": "가장 포화가 많은 노선은?"}
        Response: {
            "intent_type": "find_highlight",
            "highlight_edge": {...},
            "analysis_result": "..."
        }
    """
    try:
        # LangGraph 인스턴스 가져오기
        analytics_graph = get_analytics_graph()

        # Initial state 구성 (LangGraph 형식)
        initial_state = {
            "messages": [HumanMessage(content=request.question)]
        }

        # LangGraph 실행
        print(f"📨 Received question: {request.question}")
        result = analytics_graph.invoke(initial_state)
        print(f"✅ LangGraph execution completed")

        # State에서 결과 추출
        response_data = AnalyticsResponse(
            intent_type=result.get("intent_type", "fallback"),
            highlight_edge=result.get("highlight_edge"),
            chart_data=result.get("chart_data"),
            analysis_result=result.get("analysis_result"),
            chart_type=result.get("chart_type"),
            insights=result.get("insights")
        )

        print(f"📤 Response data:")
        print(f"   - intent_type: {response_data.intent_type}")
        print(f"   - highlight_edge: {response_data.highlight_edge}")
        print(f"   - analysis_result: {response_data.analysis_result}")
        print(f"   - insights: {len(response_data.insights) if response_data.insights else 0}개")

        return response_data

    except Exception as e:
        print(f"❌ Error in analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "analytics service healthy"}

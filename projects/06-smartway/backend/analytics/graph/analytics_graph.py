"""
Analytics Agent LangGraph 구성

Graph Flow:
    START
      ↓
    intent_analyzer
      ↓ (conditional_router)
    ┌─────────────┬──────────────┐
    ↓             ↓              ↓
get_graph_data  get_bus_data  fallback_response
    ↓             ↓              ↓
select_edge   chart_type_selector  END
    ↓             ↓
   END      generate_analytic
                  ↓
                 END
"""
from langgraph.graph import StateGraph, START, END
from analytics.types.state_types import AnalyticsState
from analytics.nodes.router import intent_analyzer, conditional_router
from analytics.nodes.find_highlight import get_graph_data, select_edge
from analytics.nodes.analysis import get_bus_data, chart_type_selector, generate_analytic
from analytics.nodes.fallback import fallback_response


def build_analytics_graph():
    """
    Analytics Agent LangGraph 구축

    Returns:
        CompiledGraph: 실행 가능한 LangGraph 인스턴스
    """
    # StateGraph 초기화
    workflow = StateGraph(AnalyticsState)

    # ============================================================
    # Nodes 추가
    # ============================================================
    workflow.add_node("intent_analyzer", intent_analyzer)

    # Find/Highlight path nodes
    workflow.add_node("get_graph_data", get_graph_data)
    workflow.add_node("select_edge", select_edge)

    # Analysis path nodes
    workflow.add_node("get_bus_data", get_bus_data)
    workflow.add_node("chart_type_selector", chart_type_selector)
    workflow.add_node("generate_analytic", generate_analytic)

    # Fallback node
    workflow.add_node("fallback_response", fallback_response)

    # ============================================================
    # Edges 구성
    # ============================================================

    # Entry point
    workflow.set_entry_point("intent_analyzer")

    # Conditional routing (intent에 따라 분기)
    workflow.add_conditional_edges(
        "intent_analyzer",
        conditional_router,
        {
            "get_graph_data": "get_graph_data",
            "get_bus_data": "get_bus_data",
            "fallback_response": "fallback_response"
        }
    )

    # Find/Highlight path: get_graph_data → select_edge → END
    workflow.add_edge("get_graph_data", "select_edge")
    workflow.add_edge("select_edge", END)

    # Analysis path: get_bus_data → chart_type_selector → generate_analytic → END
    workflow.add_edge("get_bus_data", "chart_type_selector")
    workflow.add_edge("chart_type_selector", "generate_analytic")
    workflow.add_edge("generate_analytic", END)

    # Fallback: fallback_response → END
    workflow.add_edge("fallback_response", END)

    # ============================================================
    # Compile and return
    # ============================================================
    compiled_graph = workflow.compile()

    print("✅ Analytics Agent LangGraph 구축 완료")

    return compiled_graph


# 싱글톤 패턴으로 그래프 인스턴스 생성
_analytics_graph = None


def get_analytics_graph():
    """
    Analytics Graph 싱글톤 인스턴스 반환

    Returns:
        CompiledGraph: Analytics Agent 그래프
    """
    global _analytics_graph
    if _analytics_graph is None:
        _analytics_graph = build_analytics_graph()
    return _analytics_graph

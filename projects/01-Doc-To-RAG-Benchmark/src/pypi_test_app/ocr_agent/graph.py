"""
LangGraph 그래프 정의
멀티 에이전트 워크플로우 구성
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from .state import DocumentState, update_stage
from . import config


class DocumentProcessingGraph:
    """문서 처리 그래프 정의"""
    
    def __init__(self):
        self.graph = StateGraph(DocumentState)
        self._build_graph()
    
    def _build_graph(self):
        """그래프 노드 및 엣지 구성"""
        
        # 노드 추가
        self.graph.add_node("basic_extraction", self.basic_extraction_node)
        self.graph.add_node("validation", self.validation_node)
        self.graph.add_node("fallback_handler", self.fallback_handler_node)
        self.graph.add_node("judge", self.judge_node)
        self.graph.add_node("report_generation", self.report_generation_node)
        self.graph.add_node("error_handler", self.error_handler_node)
        
        # 시작점 설정
        self.graph.set_entry_point("basic_extraction")
        
        # 조건부 엣지 추가
        self.graph.add_conditional_edges(
            "basic_extraction",
            self.route_after_extraction,
            {
                "validation": "validation",
                "error": "error_handler"
            }
        )
        
        self.graph.add_conditional_edges(
            "validation",
            self.route_after_validation,
            {
                "judge": "judge",
                "fallback": "fallback_handler",
                "error": "error_handler"
            }
        )
        
        self.graph.add_conditional_edges(
            "fallback_handler",
            self.route_after_fallback,
            {
                "validation": "validation",  # 재검증
                "judge": "judge",  # 폴백 시도 완료, 평가로
                "error": "error_handler"
            }
        )
        
        self.graph.add_edge("judge", "report_generation")
        self.graph.add_edge("report_generation", END)
        self.graph.add_edge("error_handler", END)
    
    # ========== 노드 함수 ==========
    
    def basic_extraction_node(self, state: DocumentState) -> DocumentState:
        """1단계: 기본 추출 노드"""
        from .agents.basic_extraction_agent import BasicExtractionAgent
        
        print(f"[1단계] 기본 추출 시작: {state['document_name']}")
        
        try:
            agent = BasicExtractionAgent()
            state = agent.run(state)
            state = update_stage(state, "validation")
            print(f"[OK] 기본 추출 완료: {len(state['extraction_results'])}개 결과")
            
        except Exception as e:
            print(f"[ERROR] 기본 추출 실패: {str(e)}")
            from .state import add_error
            state = add_error(state, {
                "stage": "extraction",
                "error": str(e),
                "error_type": type(e).__name__
            })
            state = update_stage(state, "failed")
        
        return state
    
    def validation_node(self, state: DocumentState) -> DocumentState:
        """2단계: 유효성 검증 노드"""
        from .agents.validation_agent import ValidationAgent
        
        print(f"[2단계] 유효성 검증 시작")
        
        try:
            agent = ValidationAgent()
            state = agent.run(state)
            print(f"[OK] 검증 완료: {len(state['validation_results'])}개 통과")
            
        except Exception as e:
            print(f"[ERROR] 검증 실패: {str(e)}")
            from .state import add_error
            state = add_error(state, {
                "stage": "validation",
                "error": str(e),
                "error_type": type(e).__name__
            })
        
        return state
    
    def fallback_handler_node(self, state: DocumentState) -> DocumentState:
        """폴백 처리 노드"""
        from .agents.validation_agent import FallbackHandler
        
        print(f"[폴백] 폴백 도구 적용 중...")
        
        try:
            handler = FallbackHandler()
            state = handler.run(state)
            print(f"[OK] 폴백 처리 완료")
            
        except Exception as e:
            print(f"[ERROR] 폴백 실패: {str(e)}")
            from .state import add_error
            state = add_error(state, {
                "stage": "fallback",
                "error": str(e),
                "error_type": type(e).__name__
            })
        
        return state
    
    def judge_node(self, state: DocumentState) -> DocumentState:
        """3단계: LLM Judge 노드"""
        from .agents.judge_agent import JudgeAgent
        
        print(f"[3단계] LLM Judge 평가 시작")
        
        try:
            agent = JudgeAgent()
            state = agent.run(state)
            state = update_stage(state, "report")
            print(f"[OK] 평가 완료: {len(state['judge_results'])}개 결과")
            
        except Exception as e:
            print(f"[ERROR] 평가 실패: {str(e)}")
            from .state import add_error
            state = add_error(state, {
                "stage": "judge",
                "error": str(e),
                "error_type": type(e).__name__
            })
            state = update_stage(state, "failed")
        
        return state
    
    def report_generation_node(self, state: DocumentState) -> DocumentState:
        """리포트 생성 노드"""
        from .agents.report_generator import ReportGenerator
        
        print(f"[리포트] 리포트 생성 중...")
        
        try:
            generator = ReportGenerator()
            state = generator.run(state)
            state = update_stage(state, "completed")
            print(f"[OK] 리포트 생성 완료")
            
        except Exception as e:
            print(f"[ERROR] 리포트 생성 실패: {str(e)}")
            from .state import add_error
            state = add_error(state, {
                "stage": "report",
                "error": str(e),
                "error_type": type(e).__name__
            })
            state = update_stage(state, "failed")
        
        return state
    
    def error_handler_node(self, state: DocumentState) -> DocumentState:
        """에러 처리 노드"""
        print(f"[ERROR] 처리 중단: {state['document_name']}")
        print(f"에러 로그: {len(state['error_log'])}개")
        
        state = update_stage(state, "failed")
        
        # 에러 로그 저장
        from .utils.file_utils import save_error_log
        save_error_log(state)
        
        return state
    
    # ========== 라우팅 함수 ==========
    
    def route_after_extraction(self, state: DocumentState) -> str:
        """추출 후 라우팅"""
        if len(state["extraction_results"]) == 0:
            return "error"
        
        # 모든 추출이 실패한 경우
        all_failed = all(
            result.status == "failed" 
            for result in state["extraction_results"]
        )
        if all_failed:
            return "error"
        
        return "validation"
    
    def route_after_validation(self, state: DocumentState) -> str:
        """
        검증 후 라우팅
        
        Note: ValidationAgent가 이제 페이지별 폴백을 내부에서 처리하므로
        fallback_handler 노드는 사용하지 않음
        """
        
        # 에러 체크
        if state["current_stage"] == "failed":
            return "error"
        
        # ValidationAgent가 폴백을 모두 처리했으므로 바로 Judge로
        # (통과/실패 여부와 무관하게 Judge가 최종 평가)
        return "judge"
    
    def route_after_fallback(self, state: DocumentState) -> str:
        """폴백 후 라우팅"""
        
        # 에러 체크
        if state["current_stage"] == "failed":
            return "error"
        
        # 새로운 추출 결과가 생성되었으면 재검증
        last_validation = state["validation_results"][-1] if state["validation_results"] else None
        if last_validation and last_validation.status == "retry":
            return "validation"
        
        # 폴백 완료, Judge로
        return "judge"
    
    def compile(self):
        """그래프 컴파일"""
        return self.graph.compile()


def create_processing_graph() -> Any:
    """문서 처리 그래프 생성 및 컴파일"""
    graph_builder = DocumentProcessingGraph()
    return graph_builder.compile()


if __name__ == "__main__":
    # 그래프 시각화 (Mermaid)
    graph = create_processing_graph()
    
    print("[INFO] LangGraph 워크플로우:")
    print("""
    START
      ↓
    [Basic Extraction]
      ↓
    [Validation] ←────┐
      ↓               │
    (Pass?)           │
      ↓               │
    Yes → [Judge]     │
      ↓               │
    No → [Fallback]───┘
      ↓
    [Report Generation]
      ↓
    END
    """)
    
    print("\n[OK] 그래프 컴파일 완료")


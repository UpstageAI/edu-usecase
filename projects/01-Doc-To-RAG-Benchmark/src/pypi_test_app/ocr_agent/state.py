"""
LangGraph 상태 정의
멀티 에이전트 시스템의 상태를 관리
"""

from typing import TypedDict, List, Dict, Optional, Any, Literal
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class PageExtractionResult:
    """페이지별 추출 결과"""
    page_num: int  # 페이지 번호
    strategy: str  # 'pdfplumber', 'pdfminer', 'pypdfium2', etc.
    text: str  # 추출된 텍스트
    bbox: List[Dict[str, Any]] = field(default_factory=list)  # 바운딩 박스 정보
    tables: List[Dict[str, Any]] = field(default_factory=list)  # 테이블 정보
    processing_time_ms: float = 0.0
    status: Literal["success", "failed"] = "success"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """기본 추출 결과 (전체 문서)"""
    strategy: str  # 'pdfplumber', 'pdfminer', 'pypdfium2', 'upstage_ocr', 'upstage_document_parse', etc.
    pages_text_path: str  # pages_text.jsonl 경로
    doc_meta_path: str  # doc_meta.json 경로
    sampled_pages: List[int] = field(default_factory=list)  # 샘플링된 페이지 번호들
    page_results: List[PageExtractionResult] = field(default_factory=list)  # 페이지별 결과
    timestamp: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0  # 처리 시간 (밀리초)
    extraction_cost_usd: float = 0.0  # API 사용 비용 (USD)
    page_count: int = 0
    total_page_count: int = 0  # 전체 페이지 수
    status: Literal["success", "failed"] = "success"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PageValidationResult:
    """페이지별 유효성 검증 결과"""
    page_num: int  # 페이지 번호
    extraction_id: str  # 연결된 추출 결과 ID
    strategy: str  # 적용된 전략
    passed: bool  # 통과 여부
    
    # 각 축별 점수/통과 여부
    scores: Dict[str, float] = field(default_factory=dict)
    pass_flags: Dict[str, bool] = field(default_factory=dict)
    
    # 폴백 정보
    fallback_path: List[str] = field(default_factory=list)
    fallback_attempts: int = 0
    improvement_delta: float = 0.0
    
    timestamp: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0
    status: Literal["pass", "fail", "retry"] = "pass"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """유효성 검증 결과 (전체 문서)"""
    extraction_id: str  # 연결된 추출 결과 ID
    strategy: str  # 적용된 전략 (예: 'pdfplumber+split')
    passed: bool  # 전체 통과 여부
    page_validations: List[PageValidationResult] = field(default_factory=list)  # 페이지별 검증 결과
    
    # 각 축별 점수/통과 여부 (평균)
    scores: Dict[str, float] = field(default_factory=dict)  # {'read': 0.85, 'sent': 0.91, ...}
    pass_flags: Dict[str, bool] = field(default_factory=dict)  # {'read': True, 'sent': True, ...}
    
    # 폴백 정보
    fallback_path: List[str] = field(default_factory=list)  # ['layout_reorder', 'table_enhancement']
    fallback_attempts: int = 0
    improvement_delta: float = 0.0  # 이전 버전 대비 개선폭
    
    # 결과 파일
    pages_text_path: str = ""
    tables_path: Optional[str] = None
    
    timestamp: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0
    status: Literal["pass", "fail", "retry"] = "pass"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PageJudgeResult:
    """페이지별 LLM Judge 평가 결과"""
    page_num: int  # 페이지 번호
    validation_id: str  # 연결된 검증 결과 ID
    strategy: str  # 평가된 전략
    
    # 점수
    S_read: float = 0.0
    S_sent: float = 0.0
    S_noise: float = 0.0
    S_table: float = 0.0
    S_fig: float = 0.0
    S_total: float = 0.0
    
    # 평가 등급
    grade: Literal["pass", "borderline", "fail"] = "fail"
    
    # 근거 및 코멘트
    rationale: str = ""
    comments: Dict[str, str] = field(default_factory=dict)
    
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JudgeResult:
    """LLM Judge 평가 결과 (전체 문서)"""
    validation_id: str  # 연결된 검증 결과 ID
    strategy: str  # 평가된 전략
    page_judges: List[PageJudgeResult] = field(default_factory=list)  # 페이지별 Judge 결과
    
    # 점수 (평균)
    S_read: float = 0.0
    S_sent: float = 0.0
    S_noise: float = 0.0
    S_table: float = 0.0
    S_fig: float = 0.0
    S_total: float = 0.0
    
    # 평가 등급
    grade: Literal["pass", "borderline", "fail"] = "fail"
    
    # 성능 지표
    ocr_speed_ms_per_page: float = 0.0
    
    # 근거 및 코멘트
    rationale: str = ""
    comments: Dict[str, str] = field(default_factory=dict)
    
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FinalSelection:
    """최종 선택된 전략"""
    document_name: str
    selected_strategy: str
    S_total: float
    ocr_speed_ms_per_page: float
    selection_rationale: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentState(TypedDict):
    """
    LangGraph의 메인 상태
    문서 처리 전체 과정의 상태를 추적
    """
    # 입력 정보
    document_path: str  # 입력 문서 경로
    document_name: str  # 문서 파일명
    document_type: str  # 파일 확장자 (.pdf, .hwp)
    
    # 메타데이터
    doc_meta: Dict[str, Any]  # 문서 메타정보
    
    # 1단계: 기본 추출 결과
    extraction_results: List[ExtractionResult]  # 여러 도구로 추출한 결과들
    
    # 2단계: 유효성 검증 결과
    validation_results: List[ValidationResult]  # 검증 통과한 결과들
    
    # 3단계: LLM Judge 결과
    judge_results: List[JudgeResult]  # 모든 전략에 대한 평가
    
    # 최종 선택
    final_selection: Optional[FinalSelection]  # 최종 선택된 전략
    
    # 실패한 조합 (Pass 못한 경우)
    failed_combinations: List[Dict[str, Any]]
    
    # 에러 로그
    error_log: List[Dict[str, Any]]
    
    # 진행 상태
    current_stage: Literal["extraction", "validation", "judge", "report", "completed", "failed"]
    
    # 타임스탬프
    start_time: datetime
    end_time: Optional[datetime]
    
    # 기타 메타데이터
    metadata: Dict[str, Any]


class SystemState(TypedDict):
    """
    시스템 전체 상태 (다중 문서 처리 시)
    """
    documents: List[DocumentState]  # 처리 중인 모든 문서
    total_documents: int
    completed_documents: int
    failed_documents: int
    
    # 전체 통계
    total_processing_time_ms: float
    total_solar_cost_usd: float
    
    # 시작/종료 시간
    system_start_time: datetime
    system_end_time: Optional[datetime]
    
    # 설정
    config: Dict[str, Any]
    
    metadata: Dict[str, Any]


def create_initial_document_state(document_path: str) -> DocumentState:
    """초기 문서 상태 생성"""
    from pathlib import Path
    path = Path(document_path)
    
    return DocumentState(
        document_path=str(document_path),
        document_name=path.name,
        document_type=path.suffix,
        doc_meta={},
        extraction_results=[],
        validation_results=[],
        judge_results=[],
        final_selection=None,
        failed_combinations=[],
        error_log=[],
        current_stage="extraction",
        start_time=datetime.now(),
        end_time=None,
        metadata={}
    )


def create_initial_system_state(config: Dict[str, Any]) -> SystemState:
    """초기 시스템 상태 생성"""
    return SystemState(
        documents=[],
        total_documents=0,
        completed_documents=0,
        failed_documents=0,
        total_processing_time_ms=0.0,
        total_solar_cost_usd=0.0,
        system_start_time=datetime.now(),
        system_end_time=None,
        config=config,
        metadata={}
    )


# 상태 업데이트 헬퍼 함수들

def add_extraction_result(state: DocumentState, result: ExtractionResult) -> DocumentState:
    """추출 결과 추가"""
    state["extraction_results"].append(result)
    return state


def add_validation_result(state: DocumentState, result: ValidationResult) -> DocumentState:
    """검증 결과 추가"""
    state["validation_results"].append(result)
    return state


def add_judge_result(state: DocumentState, result: JudgeResult) -> DocumentState:
    """평가 결과 추가"""
    state["judge_results"].append(result)
    return state


def set_final_selection(state: DocumentState, selection: FinalSelection) -> DocumentState:
    """최종 선택 설정"""
    state["final_selection"] = selection
    return state


def add_error(state: DocumentState, error: Dict[str, Any]) -> DocumentState:
    """에러 로그 추가"""
    state["error_log"].append({
        "timestamp": datetime.now(),
        **error
    })
    return state


def update_stage(state: DocumentState, stage: str) -> DocumentState:
    """현재 단계 업데이트"""
    state["current_stage"] = stage
    return state


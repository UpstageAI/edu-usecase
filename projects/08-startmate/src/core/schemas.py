# src/core/schemas.py
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, model_validator


# -------------------- atomic models --------------------

class Route(BaseModel):
    tool: str
    confidence: float = 0.0
    extra: dict[str, object] = Field(default_factory=dict)


class Doc(BaseModel):
    id: str | None = None
    title: str | None = None
    text: str = ""                 # 검색 결과 컨텍스트용 원문/스니펫
    score: float = 0.0
    snippet: str | None = None
    meta: dict[str, object] = Field(default_factory=dict)


class SearchHit(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""


# -------------------- conversation state --------------------

class State(BaseModel):
    """
    파이프라인 전체에서 공유하는 상태.
    - query: 사용자의 현재 질문
    - chat_history: 멀티턴 대화 이력 (최신 일부만 유지 권장)
    - route: 라우터 결정 결과 (tool/confidence/extra)
    - ctx: RAG로 얻은 컨텍스트 히트들(list[dict])  ← answer 노드가 주로 소비
    - docs: (옵션) 기존 문서 객체 리스트 (fallback 컨텍스트)
    - web_*: 웹 검색 단계 중간 산출물
    - query_vector: 임베딩 벡터
    - timings/debug: 실행 타이밍, 디버깅 메타
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # 입력/대화
    query: str
    conversation_id: str | None = None
    chat_history: list[dict[str, str]] = Field(default_factory=list)

    # 하위호환: 기존 'history'가 오면 chat_history로 이관
    history: list[dict[str, str]] = Field(default_factory=list)

    # 라우팅 결과
    route: Route | None = None

    # RAG 컨텍스트 & 문서
    ctx: list[dict] = Field(default_factory=list)         # ← RAG hits (표준 dict 형태)
    docs: list[Doc] = Field(default_factory=list)         # ← (옵션) 기존 Doc 객체 컨텍스트

    # 답변/출처
    answer: str | None = None
    citations: list[str] = Field(default_factory=list)

    # 웹 검색 산출물
    hits: list[SearchHit] = Field(default_factory=list)   # (검색 목록) 선택적으로 사용
    web_query: dict[str, object] = Field(default_factory=dict)
    web_pages: list[dict] = Field(default_factory=list)
    web_summary: str | None = None

    # 기타
    query_vector: list[float] = Field(default_factory=list)
    extra: dict[str, object] = Field(default_factory=dict)     # 라우터/필터 등 부가 파라미터
    debug: dict[str, object] = Field(default_factory=dict)
    timings: dict[str, float] = Field(default_factory=dict)

    # 멀티턴 관리
    summary: str | None = None          # 대화 길어질 때 요약 저장
    force_retrieve: bool = False        # 필요 시 강제 RAG 스위치

    # --- migration / normalization ---
    @model_validator(mode="after")
    def _migrate_history(self) -> "State":
        # 예전 필드(history)가 있고 chat_history가 비어있으면 이관
        if self.history and not self.chat_history:
            self.chat_history = self.history
        return self

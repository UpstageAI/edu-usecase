from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AgentStatus,
    AnalysisItem,
    Document,
    DocumentStatus,
    DocumentPage,
    PageOcrResult,
    ReportAgentStatus,
)

MERMAID_CHART = """flowchart TD
  n1([Document Upload<br/>PDF 파일 수신])
  n2[Format Detection<br/>문서 형식 분석]
  n3{Layout Analysis<br/>페이지 레이아웃 감지}
  n4[Single Page<br/>1페이지 구성]
  n5[Dual Page Detected<br/>2페이지 가로 구성 감지]
  n6[Page Splitting ✂️<br/>페이지 반으로 분할]
  n7[OCR Processing<br/>텍스트 추출 실행]
  n8[Quality Check<br/>정확도 검증]
  n9(Output Generation<br/>최종 결과 생성)
  n1 --> n2
  n2 --> n3
  n3 -- 단일 페이지 --> n4
  n3 -- 가로 2면 --> n5
  n4 --> n7
  n5 --> n6
  n6 --> n7
  n7 --> n8
  n8 --> n9
  classDef start fill:#e3f2fd,stroke:#90caf9,stroke-width:1px;
  classDef terminal fill:#e8f5e9,stroke:#a5d6a7,stroke-width:1px;
  classDef decision fill:#fff3e0,stroke:#ffb74d,stroke-width:1px;
  classDef split fill:#fce4ec,stroke:#f48fb1,stroke-width:1px;
  classDef normal fill:#f5f5f5,stroke:#bdbdbd,stroke-width:1px;
  class n1 start;
  class n2 normal;
  class n3 decision;
  class n4 normal;
  class n5 split;
  class n6 normal;
  class n7 normal;
  class n8 normal;
  class n9 terminal;"""


def _analysis_item(question: str, answer: str, page_number: int, confidence: float) -> AnalysisItem:
    return AnalysisItem(
        question=question,
        answer=answer,
        context_type="paragraph",
        page_number=page_number,
        confidence=confidence,
    )


def _agent_status(agent: str, status: AgentStatus, description: str) -> ReportAgentStatus:
    return ReportAgentStatus(agent_name=agent, status=status, description=description)


def _page_result(
    page_number: int,
    provider: str,
    *,
    document: Document,
    text: str,
    validity: str | None,
    judge: float | None,
    time_ms: float | None,
    remarks: str | None,
) -> PageOcrResult:
    return PageOcrResult(
        document=document,
        page_number=page_number,
        provider=provider,
        text_content=text,
        validity=validity,
        llm_judge_score=judge,
        processing_time_ms=time_ms,
        remarks=remarks,
    )


async def seed_if_empty(session: AsyncSession) -> None:
    existing = await session.execute(select(Document.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return

    now = datetime.utcnow()

    document_one = Document(
        id=uuid4().hex,
        original_name="국가안전시스템 개편 종합대책 대국민 보고 (12.31. 기준).pdf",
        stored_name="report_231231_processed.pdf",
        content_type="application/pdf",
        extension="pdf",
        size_bytes=1_048_576,
        pages_count=45,
        language="한국어",
        quality_score=93.2,
        status=DocumentStatus.PROCESSED,
        uploaded_at=now - timedelta(days=2, minutes=12),
        processed_at=now - timedelta(days=2, minutes=5),
        selection_rationale=(
            "Multi-Agent 파이프라인을 통해 문서 구조를 분석하고 주요 정책 요약과 통계를 추출했습니다. "
            "추가 검수가 필요한 항목은 Refiner 단계에서 플래그 처리되었습니다."
        ),
        mermaid_chart=MERMAID_CHART,
        recommended_strategy="azure_document_intelligence",
        recommendation_notes=(
            "Azure Document Intelligence가 가장 높은 LLM Judge 점수와 안정적인 처리 시간을 제공하며"
            " 페이지당 평균 처리 속도가 가장 빨라 전체 처리 시간을 단축합니다."
        ),
        benchmark_url="https://huggingface.co/datasets/GAYOEN/DOC_RAG_FINANCE_BENCHMARK",
        selected_strategy="azure_document_intelligence",
        ocr_speed_ms_per_page=820.0,
    )

    document_one.pages = [
        DocumentPage(
            page_number=1,
            text_content=(
                "제목: 국가안전시스템 개편 종합대책 대국민 보고\n\n"
                "요약\n- 본 문서는 업로드된 자료를 기반으로 Multi-Agent 시스템이 선 처리한 OCR 결과입니다.\n"
                "- 페이지 전반에 걸쳐 핵심 키워드와 문단 구조를 보존하도록 정제되었습니다.\n"
                "- 추가 검수 시 오탈자나 누락된 항목을 보완해주세요.\n\n"
                "긴 문장 테스트: "
                "이 문장은 페이지 미리보기 UI가 긴 텍스트를 어떻게 처리하는지 검증하기 위해 작성되었습니다. "
                "실제 환경에서는 정책 전문, 회의록, 조항 설명 등 한 문장이 매우 길어질 수 있으므로, "
                "줄바꿈 없이도 자연스럽게 줄바꿈 처리와 더 보기 버튼이 작동하는지 확인하는 데 활용할 수 있습니다."
            ),
            image_path=None,
        ),
        DocumentPage(
            page_number=2,
            text_content=(
                "세부 내용\n1. OCR 처리 시간: 10:32 KST\n2. 추정 카테고리: 행정/정책 문서\n3. 주요 문장\n"
                "   • 지역안전관리 체계 강화 관련 정책 방향\n"
                "   • 주관 부처 및 협업 기관 언급\n"
                "   • 향후 일정 및 후속 조치 제안\n\n"
                "NOTE: 필요한 경우 페이지 단위로 텍스트를 복사하여 편집 툴에 반영하세요."
            ),
            image_path=None,
        ),
    ]

    page_one, page_two = document_one.pages
    page_one.provider_results = [
        _page_result(
            1,
            "google_vision",
            document=document_one,
            text=page_one.text_content,
            validity="valid",
            judge=93.4,
            time_ms=820.0,
            remarks="표와 그래프의 경계선이 비교적 정확하게 추출되었습니다.",
        ),
        _page_result(
            1,
            "aws_textract",
            document=document_one,
            text=page_one.text_content,
            validity="needs_review",
            judge=91.8,
            time_ms=905.0,
            remarks="머리글 텍스트 일부가 누락되어 후속 보정이 필요합니다.",
        ),
        _page_result(
            1,
            "azure_document_intelligence",
            document=document_one,
            text=page_one.text_content,
            validity="valid",
            judge=97.1,
            time_ms=610.0,
            remarks="머리글과 본문 구조가 가장 안정적으로 추출되었습니다.",
        ),
    ]

    page_two.provider_results = [
        _page_result(
            2,
            "google_vision",
            document=document_one,
            text=page_two.text_content,
            validity="valid",
            judge=92.0,
            time_ms=860.0,
            remarks="표 항목이 대부분 정확하지만 각주가 중복 추출되었습니다.",
        ),
        _page_result(
            2,
            "aws_textract",
            document=document_one,
            text=page_two.text_content,
            validity="needs_review",
            judge=90.4,
            time_ms=940.0,
            remarks="불릿 목록 구분선이 누락되어 정규화가 필요합니다.",
        ),
        _page_result(
            2,
            "azure_document_intelligence",
            document=document_one,
            text=page_two.text_content,
            validity="valid",
            judge=96.5,
            time_ms=630.0,
            remarks="표 구조와 불릿 목록을 정확하게 인식했습니다.",
        ),
    ]

    document_one.analysis_items = [
        _analysis_item(
            "22년 대비 23년에 시정구 지역안전관리위원회 개최 횟수는 어떻게 변화했나요?",
            "2023년에는 지역안전관리위원회가 22년에 비해 3회 추가로 개최되어 정례화되었습니다.",
            page_number=10,
            confidence=95,
        ),
        _analysis_item(
            "2023년에 실시된 개선된 구조·구급훈련의 핵심 특징은 무엇인가요?",
            "2023년에는 신규 구조훈련 프로그램이 도입되었고, 실시간 상황 대응 시뮬레이션이 확장되었습니다.",
            page_number=11,
            confidence=92,
        ),
        _analysis_item(
            "재난안전 상황관리를 위해 회의 운영 면에서 어떤 변화가 있었나요?",
            "2023년 1월 이후 상황관리 회의는 통합관제센터 중심으로 운영되며 원격 참여 기능이 강화되었습니다.",
            page_number=13,
            confidence=88,
        ),
    ]

    document_one.report_agent_statuses = [
        _agent_status("Planner", AgentStatus.COMPLETED, "문서 구조 분석 및 처리 계획 수립 완료"),
        _agent_status("Judge", AgentStatus.COMPLETED, "문서 품질 및 처리 가능성 평가 완료"),
        _agent_status("Parsing", AgentStatus.COMPLETED, "OCR 및 텍스트 추출 완료"),
        _agent_status("Refiner", AgentStatus.COMPLETED, "데이터 정제 및 구조화 완료"),
        _agent_status("Reporter", AgentStatus.COMPLETED, "최종 리포트 생성 완료"),
    ]

    document_two = Document(
        id=uuid4().hex,
        original_name="2024년 주요업무 추진계획.pdf",
        stored_name="plan_2024_initial.pdf",
        content_type="application/pdf",
        extension="pdf",
        size_bytes=786_432,
        pages_count=28,
        language="한국어",
        quality_score=88.4,
        status=DocumentStatus.PROCESSING,
        uploaded_at=now - timedelta(hours=6),
        processed_at=None,
        selection_rationale="현재 Parsing 단계에서 표 추출 정합성 검증을 진행 중입니다.",
        mermaid_chart=MERMAID_CHART,
        benchmark_url=None,
    )

    document_two.pages = [
        DocumentPage(
            page_number=1,
            text_content=(
                "2024년 주요업무 추진계획 서문\n\n이번 계획은 디지털 전환과 안전 정책 강화를 목표로 합니다."
            ),
            image_path=None,
        )
    ]

    (document_two_page_one,) = document_two.pages
    document_two_page_one.provider_results = [
        _page_result(
            1,
            "google_vision",
            document=document_two,
            text=document_two_page_one.text_content,
            validity="valid",
            judge=87.5,
            time_ms=960.0,
            remarks="서문 문단이 안정적으로 추출되었으나 제목 굵기 정보가 누락되었습니다.",
        ),
        _page_result(
            1,
            "aws_textract",
            document=document_two,
            text=document_two_page_one.text_content,
            validity="degraded",
            judge=85.0,
            time_ms=1010.0,
            remarks="줄 간격이 비정상적으로 넓게 추출되어 재처리 예정입니다.",
        ),
    ]

    document_two.analysis_items = [
        _analysis_item(
            "2024년 세계경제 성장 전망치는 어떻게 제시되었나요?",
            "세계경제 성장률은 3.6%에서 3.2% 수준으로 조정되었습니다.",
            page_number=4,
            confidence=91,
        ),
        _analysis_item(
            "2024년에 선실업 'K-스카우디' 제도의 주요 계획은 무엇인가요?",
            "해운 인력 양성을 위해 선박 안전 모니터링 훈련과 국제 교류 프로그램이 확대됩니다.",
            page_number=12,
            confidence=87,
        ),
    ]

    document_two.report_agent_statuses = [
        _agent_status("Planner", AgentStatus.COMPLETED, "카테고리 분류 및 처리 전략 수립"),
        _agent_status("Judge", AgentStatus.COMPLETED, "OCR 품질 사전 평가"),
        _agent_status("Parsing", AgentStatus.RUNNING, "표 인식 모델 재시도 중"),
        _agent_status("Refiner", AgentStatus.PENDING, "Parsing 완료 후 실행 예정"),
        _agent_status("Reporter", AgentStatus.PENDING, "정제 데이터 수신 대기"),
    ]

    session.add_all([document_one, document_two])
    await session.flush()

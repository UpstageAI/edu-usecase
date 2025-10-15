from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import os
from pathlib import Path

from ..models import (
    AnalysisItem,
    Document,
    DocumentPage,
    DocumentStatus,
    ReportAgentStatus,
)
from ..schemas import (
    AnalysisItemOut,
    AnalysisListResponse,
    DocumentInsightsResponse,
    DocumentListResponse,
    DocumentSummary,
    PagePreviewOut,
    PageProviderResultOut,
    ProviderEvaluationOut,
    ProviderSelectionRequest,
    ReportAgentStatusOut,
    UploadResponse,
)
from ..ocr_pipeline import process_document
from ..storage import UploadStorage
from .dependencies import get_session, get_storage

from anyio import to_thread
from PyPDF2 import PdfReader

def _count_pdf_pages_sync(path: str) -> int:
    with open(path, "rb") as f:
        reader = PdfReader(f)
        if reader.is_encrypted:
            # 빈 비번 시도(일부 파일은 비번 없이 해제됨). 그래도 잠겨 있으면 거절
            try:
                reader.decrypt("")
            except Exception:
                pass
            if reader.is_encrypted:
                raise HTTPException(status_code=400, detail="비밀번호로 잠긴 PDF는 지원하지 않습니다.")
        return len(reader.pages)

router = APIRouter()


_PROVIDER_DISPLAY_NAMES = {
    "google_vision": "Google Vision API",
    "aws_textract": "AWS Textract",
    "azure_document_intelligence": "Azure Document Intelligence",
    "pdfplumber": "PDFPlumber",
    "pdfminer": "PDFMiner",
    "pypdfium2": "PyPDFium2",
    "upstage_ocr": "Upstage OCR",
    "upstage_document_parse": "Upstage Document Parse",
}


def _provider_display_name(provider: str | None) -> str:
    if not provider:
        return "-"
    if provider in _PROVIDER_DISPLAY_NAMES:
        return _PROVIDER_DISPLAY_NAMES[provider]
    if "+" in provider:
        parts = provider.split("+")
        formatted = [
            _PROVIDER_DISPLAY_NAMES.get(part, part.replace("_", " ").title())
            for part in parts
        ]
        return " + ".join(formatted)
    return provider.replace("_", " ").title()


def _build_document_summary(
    document: Document,
    *,
    analysis_items_count: int,
    recommended: str | None = None,
    recommendation_reason: str | None = None,
) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        original_name=document.original_name,
        stored_name=document.stored_name,
        size_bytes=document.size_bytes,
        extension=document.extension,
        language=document.language,
        status=document.status,
        uploaded_at=document.uploaded_at,
        processed_at=document.processed_at,
        quality_score=document.quality_score,
        pages_count=document.pages_count,
        analysis_items_count=analysis_items_count,
        recommended_strategy=recommended if recommended is not None else document.recommended_strategy,
        recommendation_notes=(
            recommendation_reason if recommendation_reason is not None else document.recommendation_notes
        ),
        selected_strategy=document.selected_strategy,
        selection_rationale=document.selection_rationale,
        ocr_speed_ms_per_page=document.ocr_speed_ms_per_page,
        benchmark_url=document.benchmark_url,
    )


def _aggregate_provider_metrics(document: Document) -> dict[str, dict[str, object]]:
    stats: dict[str, dict[str, object]] = {}
    for result in document.page_provider_results:
        provider = (result.provider or "").strip()
        if not provider:
            continue
        entry = stats.setdefault(
            provider,
            {
                "scores": [],
                "times": [],
                "costs": [],
                "total_cost": 0.0,
                "pages": set(),
                "remarks": [],
            },
        )
        if result.llm_judge_score is not None:
            entry["scores"].append(result.llm_judge_score)
        if result.processing_time_ms is not None:
            entry["times"].append(result.processing_time_ms)
        if result.cost_per_page is not None:
            entry["costs"].append(result.cost_per_page)
            entry["total_cost"] = float(entry.get("total_cost", 0.0)) + float(result.cost_per_page)
        entry["pages"].add(result.page_number)
        if result.remarks:
            entry["remarks"].append((result.page_number, result.remarks))

    aggregated: dict[str, dict[str, object]] = {}
    for provider, entry in stats.items():
        scores: list[float] = entry["scores"]  # type: ignore[assignment]
        times: list[float] = entry["times"]  # type: ignore[assignment]
        costs: list[float] = entry["costs"]  # type: ignore[assignment]
        remarks: list[tuple[int, str]] = entry["remarks"]  # type: ignore[assignment]
        aggregated[provider] = {
            "average_score": (sum(scores) / len(scores)) if scores else None,
            "average_time": (sum(times) / len(times)) if times else None,
            "average_cost": (sum(costs) / len(costs)) if costs else None,
            "total_cost": entry.get("total_cost") if costs else None,
            "pages_count": len(entry["pages"]),  # type: ignore[arg-type]
            "representative_remark": next(
                (remark for _, remark in sorted(remarks, key=lambda item: item[0]) if remark),
                None,
            )
            if remarks
            else None,
        }
    return aggregated


def _calculate_recommendation(
    document: Document,
    metrics: dict[str, dict[str, object]] | None = None,
) -> tuple[str | None, str | None]:
    if document.recommended_strategy and document.recommendation_notes:
        return document.recommended_strategy, document.recommendation_notes

    metrics = metrics or _aggregate_provider_metrics(document)
    if not metrics:
        return document.recommended_strategy, document.recommendation_notes

    quality_values = [
        value["average_score"]
        for value in metrics.values()
        if value.get("average_score") is not None
    ]
    time_values = [
        value["average_time"]
        for value in metrics.values()
        if value.get("average_time") is not None
    ]
    cost_values = [
        value["total_cost"]
        for value in metrics.values()
        if value.get("total_cost") is not None
    ]

    q_min = min(quality_values) if quality_values else 0.0
    q_max = max(quality_values) if quality_values else 0.0
    t_min = min(time_values) if time_values else 0.0
    t_max = max(time_values) if time_values else 0.0
    c_min = min(cost_values) if cost_values else 0.0
    c_max = max(cost_values) if cost_values else 0.0

    best_provider: str | None = None
    best_score = float("-inf")
    for provider, value in metrics.items():
        score = float(value.get("average_score") or 0.0)
        time_ms = float(value.get("average_time") or 0.0)
        total_cost = float(value.get("total_cost") or 0.0)

        if quality_values and q_max != q_min:
            quality_component = (score - q_min) / (q_max - q_min)
        elif quality_values:
            quality_component = 1.0
        else:
            quality_component = 0.0

        if time_values and t_max != t_min:
            base_time = time_ms if value.get("average_time") is not None else t_max
            time_component = (t_max - base_time) / (t_max - t_min)
        elif time_values:
            time_component = 1.0
        else:
            time_component = 0.0

        if cost_values and c_max != c_min:
            cost_component = (c_max - total_cost) / (c_max - c_min)
        elif cost_values:
            cost_component = 1.0
        else:
            cost_component = 0.0

        composite = (0.5 * quality_component) + (0.3 * time_component) + (0.2 * cost_component)
        if composite > best_score:
            best_score = composite
            best_provider = provider

    if best_provider is None:
        best_provider = next(iter(metrics))

    stats = metrics[best_provider]
    reason_parts: list[str] = []
    if stats.get("average_score") is not None:
        reason_parts.append(f"LLM-Judge 점수 {stats['average_score']:.1f}")
    if stats.get("average_time") is not None:
        reason_parts.append(f"페이지당 처리 시간 {stats['average_time']:.0f}ms")
    if stats.get("total_cost") is not None:
        reason_parts.append(f"총 비용 {stats['total_cost']:.2f}원")

    display_name = _provider_display_name(best_provider)
    if reason_parts:
        reason = f"{display_name}가 {' 및 '.join(reason_parts)} 기준으로 가장 균형 잡힌 성능을 보였습니다."
    else:
        reason = f"{display_name}가 페이지별 OCR 평가에서 일관된 결과를 기록했습니다."

    return best_provider, reason


def _build_provider_evaluations(
    document: Document,
    metrics: dict[str, dict[str, object]] | None = None,
) -> List[ProviderEvaluationOut]:
    metrics = metrics or _aggregate_provider_metrics(document)
    if not metrics:
        return []

    total_pages = document.pages_count or len(document.pages) or 1
    quality_values = [
        value["average_score"]
        for value in metrics.values()
        if value.get("average_score") is not None
    ]
    time_values = [
        value["average_time"]
        for value in metrics.values()
        if value.get("average_time") is not None
    ]
    cost_totals = [
        value["total_cost"]
        for value in metrics.values()
        if value.get("total_cost") is not None
    ]
    max_quality = max(quality_values) if quality_values else None
    min_time = min(time_values) if time_values else None
    min_cost = min(cost_totals) if cost_totals else None

    response: List[ProviderEvaluationOut] = []
    for provider, value in metrics.items():
        score_raw = value.get("average_score")
        time_raw = value.get("average_time")
        cost_raw = value.get("average_cost")
        total_cost_raw = value.get("total_cost")
        llm_score = float(score_raw) if score_raw is not None else 0.0
        time_per_page = float(time_raw) if time_raw is not None else 0.0
        total_time_ms = time_per_page * total_pages if time_raw is not None else 0.0
        cost_per_page = float(cost_raw) if cost_raw is not None else None
        total_cost = float(total_cost_raw) if total_cost_raw is not None else (
            (cost_per_page * total_pages) if (cost_per_page is not None and total_pages) else None
        )

        response.append(
            ProviderEvaluationOut(
                provider=provider,
                display_name=_provider_display_name(provider),
                llm_judge_score=llm_score,
                time_per_page_ms=time_per_page,
                estimated_total_time_ms=total_time_ms,
                cost_per_page=cost_per_page,
                estimated_total_cost=total_cost,
                quality_notes=value.get("representative_remark"),
                latency_ms=None,
                is_best_quality=(
                    score_raw is not None and max_quality is not None and score_raw == max_quality
                ),
                is_fastest=(
                    time_raw is not None and min_time is not None and time_raw == min_time
                ),
                is_most_affordable=(
                    total_cost is not None
                    and min_cost is not None
                    and total_cost == min_cost
                ),
            )
        )
    return response


def _coerce_validity(value: str | None) -> str | bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "1", "y", "yes", "valid"}:
        return True
    if lowered in {"false", "0", "n", "no", "invalid"}:
        return False
    return value


def _build_page_previews(document: Document) -> List[PagePreviewOut]:
    previews: List[PagePreviewOut] = []
    for page in document.pages:
        provider_results: List[PageProviderResultOut] = []
        for result in getattr(page, "provider_results", []) or []:
            provider_results.append(
                PageProviderResultOut(
                    provider=result.provider,
                    display_name=_provider_display_name(result.provider),
                    text_content=result.text_content or page.text_content,
                    validity=_coerce_validity(result.validity),
                    llm_judge_score=result.llm_judge_score,
                    processing_time_ms=result.processing_time_ms,
                    cost_per_page=result.cost_per_page,
                    remarks=result.remarks,
                )
            )

        previews.append(
            PagePreviewOut(
                page_number=page.page_number,
                image_path=page.image_path,
                text_content=page.text_content,
                provider_results=provider_results or None,
            )
        )
    return previews


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(session: AsyncSession = Depends(get_session)) -> DocumentListResponse:
    stmt = (
        select(Document, func.count(AnalysisItem.id).label("analysis_items_count"))
        .outerjoin(AnalysisItem, AnalysisItem.document_id == Document.id)
        .group_by(Document.id)
        .order_by(Document.uploaded_at.desc())
    )
    result = await session.execute(stmt)
    items: List[DocumentSummary] = []
    for document, analysis_items_count in result.all():
        items.append(
            _build_document_summary(
                document,
                analysis_items_count=int(analysis_items_count or 0),
            )
        )
    return DocumentListResponse(items=items)


@router.get("/analysis-items", response_model=AnalysisListResponse)
async def list_analysis_items(session: AsyncSession = Depends(get_session)) -> AnalysisListResponse:
    stmt = (
        select(AnalysisItem, Document.original_name.label("document_name"))
        .join(Document, AnalysisItem.document_id == Document.id)
        .order_by(AnalysisItem.page_number.asc())
    )
    result = await session.execute(stmt)
    rows = result.all()
    items = [
        AnalysisItemOut(
            id=analysis.id,
            document_id=analysis.document_id,
            question=analysis.question,
            answer=analysis.answer,
            context_type=analysis.context_type,
            confidence=analysis.confidence,
            page_number=analysis.page_number,
            document_name=document_name,
        )
        for analysis, document_name in rows
    ]
    return AnalysisListResponse(items=items, total_items=len(items))


@router.get("/documents/{document_id}/insights", response_model=DocumentInsightsResponse)
async def get_document_insights(
    document_id: str,
    session: AsyncSession = Depends(get_session),
) -> DocumentInsightsResponse:
    document = await session.get(
        Document,
        document_id,
        options=[
            selectinload(Document.analysis_items),
            selectinload(Document.pages).selectinload(DocumentPage.provider_results),
            selectinload(Document.report_agent_statuses),
            selectinload(Document.page_provider_results),
        ],
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")

    metrics = _aggregate_provider_metrics(document)
    recommended, reason = _calculate_recommendation(document, metrics)

    summary = _build_document_summary(
        document,
        analysis_items_count=len(document.analysis_items),
        recommended=recommended,
        recommendation_reason=reason,
    )

    provider_evaluations = _build_provider_evaluations(document, metrics)
    pages = _build_page_previews(document)
    agent_statuses = [
        ReportAgentStatusOut(
            agent_name=item.agent_name,
            status=item.status,
            description=item.description,
        )
        for item in document.report_agent_statuses
    ]

    return DocumentInsightsResponse(
        document=summary,
        provider_evaluations=provider_evaluations,
        pages=pages,
        agent_statuses=agent_statuses,
        mermaid_chart=document.mermaid_chart,
        selection_rationale=document.selection_rationale,
    )


@router.put("/documents/{document_id}/selection", response_model=DocumentSummary)
async def update_document_selection(
    document_id: str,
    payload: ProviderSelectionRequest,
    session: AsyncSession = Depends(get_session),
) -> DocumentSummary:
    document = await session.get(
        Document,
        document_id,
        options=[selectinload(Document.analysis_items), selectinload(Document.page_provider_results)],
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")

    metrics = _aggregate_provider_metrics(document)
    if payload.provider not in metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="선택한 제공자가 문서 평가 데이터에 존재하지 않습니다.",
        )

    document.selected_strategy = payload.provider
    await session.commit()

    recommended, reason = _calculate_recommendation(document, metrics)

    return _build_document_summary(
        document,
        analysis_items_count=len(document.analysis_items),
        recommended=recommended,
        recommendation_reason=reason,
    )


@router.post("/uploads", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    request: Request,
    file: UploadFile = File(..., description="업로드할 파일을 선택하세요."),
    storage: UploadStorage = Depends(get_storage),
    session: AsyncSession = Depends(get_session),
) -> UploadResponse:
    api_key = (request.headers.get("x-ocr-api-key") or "").strip()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API 키가 필요합니다.")

    if file is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="최소 한 개의 파일을 업로드해야 합니다.")

    metadata_list = await storage.save_files([file])
    if not metadata_list:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="파일 저장에 실패했습니다.")

    metadata = metadata_list[0]
    file_path = storage.base_directory / metadata.stored_name

    pages_count = 0
    if (file.content_type == "application/pdf") or (metadata.extension and metadata.extension.lower() == ".pdf"):
        pages_count = await to_thread.run_sync(_count_pdf_pages_sync, str(file_path))

    document = Document(
        id=metadata.id,
        original_name=metadata.original_name,
        stored_name=metadata.stored_name,
        content_type=file.content_type,
        extension=metadata.extension,
        size_bytes=metadata.size_bytes,
        status=DocumentStatus.PROCESSING,
        uploaded_at=metadata.uploaded_at,
        pages_count=pages_count,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)

    try:
        await process_document(
            document=document,
            file_path=file_path,
            storage=storage,
            session=session,
            api_key=api_key,
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        document = await session.get(Document, document.id)
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OCR 처리 중 알 수 없는 오류가 발생했습니다.",
            ) from exc

        document.status = DocumentStatus.FAILED
        document.selection_rationale = f"OCR 처리 실패: {exc}"
        document.processed_at = datetime.utcnow()
        document.recommended_strategy = None
        document.recommendation_notes = None
        document.selected_strategy = None
        document.quality_score = None
        document.ocr_speed_ms_per_page = None
        await session.commit()
    finally:
        await session.refresh(document)

    analysis_items_count = await session.scalar(
        select(func.count(AnalysisItem.id)).where(AnalysisItem.document_id == document.id)
    )
    summary = _build_document_summary(
        document,
        analysis_items_count=int(analysis_items_count or 0),
    )
    return UploadResponse(document=summary)


@router.get("/uploads", response_model=DocumentListResponse)
async def legacy_uploads(session: AsyncSession = Depends(get_session)) -> DocumentListResponse:
    return await list_documents(session)

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from anyio import to_thread
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AgentStatus,
    Document,
    DocumentPage,
    DocumentStatus,
    PageOcrResult,
    ReportAgentStatus,
)
from .ocr_agent import create_initial_document_state, create_processing_graph
from .ocr_agent import config as agent_config
from .ocr_agent.state import (
    DocumentState,
    ExtractionResult,
    FinalSelection,
    JudgeResult,
    PageJudgeResult,
    PageValidationResult,
    ValidationResult,
)
from .storage import UploadStorage


def _run_agent(document_path: Path, agent_root: Path) -> DocumentState:
    """Synchronously execute the OCR agent and return the final state."""

    agent_config.set_project_root(agent_root, ensure_directories=True)
    state = create_initial_document_state(str(document_path))
    graph = create_processing_graph()
    return graph.invoke(state)


async def process_document(
    *,
    document: Document,
    file_path: Path,
    storage: UploadStorage,
    session: AsyncSession,
    api_key: Optional[str] = None,
) -> DocumentState:
    """Run the OCR pipeline with the provided API key and persist results."""

    agent_root = storage.base_directory.parent / "ocr_agent"
    if api_key:
        agent_config.set_api_key(api_key)
    try:
        state = await to_thread.run_sync(_run_agent, file_path, agent_root)
        await _apply_state(session=session, document=document, state=state)
        return state
    finally:
        if api_key:
            agent_config.set_api_key(None)


async def _apply_state(*, session: AsyncSession, document: Document, state: DocumentState) -> None:
    """Update the database according to the OCR agent *state*."""

    document.processed_at = datetime.utcnow()

    extraction_map: Dict[str, ExtractionResult] = {result.strategy: result for result in state.get("extraction_results", [])}
    validation_map: Dict[str, ValidationResult] = {result.strategy: result for result in state.get("validation_results", [])}
    judge_map: Dict[str, JudgeResult] = {result.strategy: result for result in state.get("judge_results", [])}

    final_selection: Optional[FinalSelection] = state.get("final_selection")
    if not final_selection:
        document.status = DocumentStatus.FAILED
        document.selection_rationale = _summarize_failure(state)
        document.recommended_strategy = None
        document.recommendation_notes = None
        document.selected_strategy = None
        document.quality_score = None
        document.ocr_speed_ms_per_page = None
        await _replace_agent_statuses(session, document, state)
        return

    selected_strategy = final_selection.selected_strategy
    selected_extraction = extraction_map.get(selected_strategy)
    selected_validation = validation_map.get(selected_strategy)

    document.status = DocumentStatus.PROCESSED
    document.quality_score = float(final_selection.S_total)
    document.selected_strategy = selected_strategy
    document.recommended_strategy = selected_strategy
    document.recommendation_notes = final_selection.selection_rationale
    document.selection_rationale = final_selection.selection_rationale
    document.ocr_speed_ms_per_page = float(final_selection.ocr_speed_ms_per_page)

    if selected_extraction:
        document.pages_count = selected_extraction.total_page_count or selected_extraction.page_count
    else:
        document.pages_count = len(selected_validation.page_validations) if selected_validation else 0

    page_lookup = await _replace_document_pages(
        session=session,
        document=document,
        selected_strategy=selected_strategy,
        extraction_map=extraction_map,
        validation_map=validation_map,
    )

    await _replace_page_results(
        session=session,
        document=document,
        extraction_map=extraction_map,
        validation_map=validation_map,
        judge_map=judge_map,
        page_lookup=page_lookup,
    )

    await _replace_agent_statuses(session, document, state)


async def _replace_document_pages(
    *,
    session: AsyncSession,
    document: Document,
    selected_strategy: str,
    extraction_map: Dict[str, ExtractionResult],
    validation_map: Dict[str, ValidationResult],
) -> Dict[int, DocumentPage]:
    """Rebuild `DocumentPage` entries for the processed document."""

    await session.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
    await session.flush()

    preferred_validation = validation_map.get(selected_strategy)
    page_texts: Dict[int, str] = {}

    if preferred_validation:
        for item in preferred_validation.page_validations:
            text = _resolve_page_text(item, extraction_map.get(selected_strategy))
            if text:
                page_texts[item.page_num] = text

    for validation in validation_map.values():
        for item in validation.page_validations:
            if item.page_num not in page_texts:
                text = _resolve_page_text(item, extraction_map.get(validation.strategy))
                if text:
                    page_texts[item.page_num] = text

    pages_to_add = []
    for page_number in sorted(page_texts):
        page = DocumentPage(
            document_id=document.id,
            page_number=page_number,
            text_content=page_texts[page_number],
            image_path=None,
        )
        pages_to_add.append(page)

    if pages_to_add:
        session.add_all(pages_to_add)
        await session.flush()

    return {page.page_number: page for page in pages_to_add}


async def _replace_page_results(
    *,
    session: AsyncSession,
    document: Document,
    extraction_map: Dict[str, ExtractionResult],
    validation_map: Dict[str, ValidationResult],
    judge_map: Dict[str, JudgeResult],
    page_lookup: Dict[int, DocumentPage],
) -> None:
    """Rebuild `PageOcrResult` entries derived from judge outputs."""

    await session.execute(delete(PageOcrResult).where(PageOcrResult.document_id == document.id))
    await session.flush()

    page_validation_lookup: Dict[Tuple[str, int], PageValidationResult] = {}
    for strategy, validation in validation_map.items():
        for page_validation in validation.page_validations:
            page_validation_lookup[(strategy, page_validation.page_num)] = page_validation

    results_to_add: list[PageOcrResult] = []
    for strategy, judge_result in judge_map.items():
        extraction = extraction_map.get(strategy)
        cost_per_page = _calculate_cost_per_page(extraction)

        for page_judge in judge_result.page_judges:
            page_obj = page_lookup.get(page_judge.page_num)
            if not page_obj:
                page_obj = DocumentPage(
                    document_id=document.id,
                    page_number=page_judge.page_num,
                    text_content=_fallback_page_text(
                        strategy=strategy,
                        page_num=page_judge.page_num,
                        extraction_map=extraction_map,
                        validation_lookup=page_validation_lookup,
                    ),
                    image_path=None,
                )
                session.add(page_obj)
                await session.flush()
                page_lookup[page_obj.page_number] = page_obj

            page_validation = page_validation_lookup.get((strategy, page_judge.page_num))
            page_text = _fallback_page_text(
                strategy=strategy,
                page_num=page_judge.page_num,
                extraction_map=extraction_map,
                validation_lookup=page_validation_lookup,
            )

            page_result = PageOcrResult(
                document_id=document.id,
                document_page_id=page_obj.id,
                page_number=page_judge.page_num,
                provider=strategy,
                text_content=page_text,
                validity=_validation_flag(page_validation),
                llm_judge_score=float(page_judge.S_total),
                processing_time_ms=_processing_time(
                    page_validation=page_validation,
                    extraction=extraction,
                    page_num=page_judge.page_num,
                ),
                cost_per_page=cost_per_page,
                remarks=_build_remarks(page_validation, page_judge),
            )
            results_to_add.append(page_result)

    if results_to_add:
        session.add_all(results_to_add)
        await session.flush()


async def _replace_agent_statuses(
    session: AsyncSession,
    document: Document,
    state: DocumentState,
) -> None:
    """Replace `ReportAgentStatus` entries to reflect the pipeline run."""

    await session.execute(delete(ReportAgentStatus).where(ReportAgentStatus.document_id == document.id))

    errors = {entry.get("stage"): entry for entry in state.get("error_log", [])}

    def build_status(stage: str, completed: bool, description: str) -> ReportAgentStatus:
        error = errors.get(stage)
        if error:
            status = AgentStatus.FAILED
            desc = error.get("error", description)
        elif completed:
            status = AgentStatus.COMPLETED
            desc = description
        else:
            status = AgentStatus.PENDING
            desc = description
        return ReportAgentStatus(
            document_id=document.id,
            agent_name=stage,
            status=status,
            description=desc,
        )

    extraction_done = len(state.get("extraction_results", [])) > 0
    validation_done = len(state.get("validation_results", [])) > 0
    judge_done = len(state.get("judge_results", [])) > 0
    report_done = state.get("current_stage") == "completed"

    statuses = [
        build_status("extraction", extraction_done, f"추출 {len(state.get('extraction_results', []))}건"),
        build_status("validation", validation_done, f"검증 {len(state.get('validation_results', []))}건"),
        build_status("judge", judge_done, f"Judge {len(state.get('judge_results', []))}건"),
        build_status("report", report_done, "리포트 생성"),
    ]

    if statuses:
        session.add_all(statuses)
        await session.flush()


def _summarize_failure(state: DocumentState) -> str:
    errors = state.get("error_log") or []
    if not errors:
        return "OCR 에이전트가 최종 결과를 생성하지 못했습니다."
    last_error = errors[-1]
    stage = last_error.get("stage", "unknown")
    message = last_error.get("error", "원인 불명")
    return f"{stage} 단계 실패: {message}"


def _resolve_page_text(page_validation: PageValidationResult, extraction: Optional[ExtractionResult]) -> str:
    meta = page_validation.metadata or {}
    text = meta.get("page_text")
    if text:
        return text
    if extraction:
        for page in extraction.page_results:
            if page.page_num == page_validation.page_num:
                return page.text
    return ""


def _fallback_page_text(
    *,
    strategy: str,
    page_num: int,
    extraction_map: Dict[str, ExtractionResult],
    validation_lookup: Dict[Tuple[str, int], PageValidationResult],
) -> str:
    validation = validation_lookup.get((strategy, page_num))
    if validation:
        meta = validation.metadata or {}
        text = meta.get("page_text")
        if text:
            return text
    extraction = extraction_map.get(strategy)
    if extraction:
        for page in extraction.page_results:
            if page.page_num == page_num:
                return page.text
    return ""


def _validation_flag(page_validation: Optional[PageValidationResult]) -> Optional[str]:
    if page_validation is None:
        return None
    return "pass" if page_validation.passed else "fail"


def _processing_time(
    *,
    page_validation: Optional[PageValidationResult],
    extraction: Optional[ExtractionResult],
    page_num: int,
) -> Optional[float]:
    if page_validation and page_validation.processing_time_ms:
        return float(page_validation.processing_time_ms)
    if extraction:
        for page in extraction.page_results:
            if page.page_num == page_num:
                return float(page.processing_time_ms)
    return None


def _calculate_cost_per_page(extraction: Optional[ExtractionResult]) -> Optional[float]:
    if not extraction or extraction.page_count == 0:
        return None
    return float(extraction.extraction_cost_usd or 0.0) / float(extraction.page_count)


def _build_remarks(
    page_validation: Optional[PageValidationResult],
    page_judge: PageJudgeResult,
) -> Optional[str]:
    payload = {
        "judge_grade": page_judge.grade,
        "judge_rationale": page_judge.rationale,
        "judge_scores": {
            "S_read": page_judge.S_read,
            "S_sent": page_judge.S_sent,
            "S_noise": page_judge.S_noise,
            "S_table": page_judge.S_table,
            "S_fig": page_judge.S_fig,
        },
    }

    if page_validation:
        meta = page_validation.metadata or {}
        payload.update(
            {
                "llm_confidence": meta.get("llm_confidence"),
                "llm_reason": meta.get("llm_reason"),
                "llm_issues": meta.get("llm_issues"),
                "fallback_path": page_validation.fallback_path,
            }
        )

    try:
        return json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError):
        return None

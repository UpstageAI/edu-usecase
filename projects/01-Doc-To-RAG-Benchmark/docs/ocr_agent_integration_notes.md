# OCR Agent Integration Notes

## Current FastAPI Data Model Touchpoints
- `Document` represents an uploaded file and drives the UI summary view.
  - Key fields consumed by the frontend: `status`, `processed_at`, `quality_score`, `pages_count`, `recommended_strategy`, `recommendation_notes`, `selected_strategy`, `selection_rationale`, `ocr_speed_ms_per_page`.
- `DocumentPage` feeds the page preview drawer; the UI expects `text_content` and optional `image_path`.
- `PageOcrResult` backs the per-page provider comparisons; the UI expects multiple providers (strategies) per page with judge scores, validity flags, processing time, cost, and remarks.
- `ReportAgentStatus` powers the activity timeline for stages like OCR, validation, judge, and reporting.

## OCR Agent Output Summary
- Entry point: `create_processing_graph().invoke(initial_state)` in `doc-ocr`.
- Intermediate data structures declared in `state.py`:
  - `ExtractionResult`: per strategy (pdfplumber, pdfminer, pypdfium2, upstage_ocr, upstage_document_parse) with sampled `PageExtractionResult` entries and metadata such as processing time and API cost.
  - `ValidationResult`: captures pass/fail per page, fallback attempts, axis scores, and overall averages.
  - `JudgeResult`: aggregates page-level Solar LLM scores (`S_read`, `S_sent`, `S_noise`, `S_table`, `S_fig`, `S_total`) plus speed metrics.
  - `FinalSelection`: chosen strategy with composite reasoning and metadata.
  - `error_log` and `failed_combinations` record pipeline issues.
- Report generator persists JSON/CSV artifacts under `config.REPORTS_DIR` and `config.TABLES_DIR` and mirrors the structure the state keeps in memory.

## Proposed Data Mapping
| OCR Agent Datum | Target Model | Notes |
| --- | --- | --- |
| `FinalSelection.selected_strategy` | `Document.selected_strategy` | Drives UI recommendation & highlights.
| `FinalSelection.S_total` (0-100) | `Document.quality_score` | Stored as LangGraph judge score.
| `FinalSelection.selection_rationale` | `Document.selection_rationale` | Provides human-readable summary.
| `FinalSelection.ocr_speed_ms_per_page` | `Document.ocr_speed_ms_per_page` | Caches per-page latency for UI badges.
| Highest-ranked strategy metadata | `Document.recommended_strategy` / `recommendation_notes` | Mirror `FinalSelection` to keep UI copy minimal.
| `JudgeResult` entries per strategy | `PageOcrResult` (per page) | Persist Solar LLM scores/time/cost/remarks per page-strategy combo.
| `PageExtractionResult.text` for selected strategy | `DocumentPage.text_content` | Use sampled pages; non-sampled pages remain absent until agent supports full extraction.
| `PageValidationResult.pass_flags` & fallback info | `PageOcrResult.validity` / `remarks` | Encode axis failures and fallback trail in remarks JSON or formatted text.
| Agent stages (extraction, validation, judge, report) | `ReportAgentStatus` | Set to `completed` / `failed` with optional descriptions.
| `state.error_log` | `ReportAgentStatus` or `Document.selection_rationale` | Append final failure reason when pipeline fails.

## Schema & API Adjustments Needed
1. Ensure `Document.quality_score` stores Solar score (already `Float`).
2. Populate `Document.pages_count` with `ExtractionResult.total_page_count` for the selected strategy.
3. Populate `DocumentPage.image_path` as available (agent does not currently render images; leave `None`).
4. `PageOcrResult.validity` currently stores a string/bool – reuse for pass/fail; embed axis scores inside `remarks` as JSON.
5. Potential addition: lightweight helper table/function to persist judge averages if we need to display provider-level aggregates quickly; otherwise compute on demand from `PageOcrResult`.
6. Update `/uploads` workflow:
   - Save upload via `UploadStorage` (existing behavior).
   - Create DB `Document` row with status `processing` and kick off OCR agent.
   - Run agent pipeline (synchronously for now) using the saved file path; update DB transactionally with results.
   - On success: mark `Document.status = processed`, set `processed_at`, insert `DocumentPage` & `PageOcrResult` records, and seed `ReportAgentStatus` timeline.
   - On failure: set `Document.status = failed` and capture reason.
7. Configuration: align OCR agent directories under `UploadStorage.base_directory` (e.g., `.pypi_test_app/ocr_agent/{input,output,temp}`) to keep assets alongside FastAPI storage.

## Outstanding Design Questions
- Should uploads return immediately (async background task) or block until OCR completes? Blocking simplifies data consistency but increases latency.
- Do we need full-page extraction (not just sampled pages) for the UI? If yes, extend agent to export full texts.
- Error handling strategy for partial failures (e.g., one strategy failing while others succeed).

These points drive upcoming implementation tasks in steps 2–4 of the integration plan.

## Backend Integration Highlights
- OCR agent code is vendored under `src/pypi_test_app/ocr_agent` with relative imports and a configurable storage root (`config.set_project_root`).
- `src/pypi_test_app/ocr_pipeline.py` orchestrates the agent execution, transforms LangGraph state into SQLAlchemy models, and records stage-by-stage status.
- `/api/uploads` now saves the file via `UploadStorage`, marks the document as `processing`, synchronously runs the OCR pipeline, and responds with the fully populated document summary. 업로드 요청의 `x-ocr-api-key` 헤더 값은 `SOLAR_API_KEY`로 주입되어 LangGraph 실행에 사용됩니다.
- Provider display names include the agent strategies (PDFPlumber, PDFMiner, PyPDFium2, Upstage OCR/Document Parse) and fall back gracefully for composite strategies like `pdfplumber+layout_reorder`.
- `setup.py` has been extended with the agent’s runtime dependencies (`langgraph`, `pdfplumber`, `pdfminer.six`, `pypdf`, `pypdfium2`, `requests`, `python-dotenv`).

## Next Steps / Verification Checklist
1. **Environment variables** – optionally configure `OCR_AGENT_BASE_DIR`. `SOLAR_API_KEY`는 요청 헤더에서 전달되므로 전역 설정은 선택 사항입니다.
2. **Dependency install** – run `pip install -e .` (or the preferred workflow) to pull in the new libraries before launching the backend.
3. **Smoke test** – start the FastAPI server and upload a sample PDF, confirm that the response returns `status: processed`, `selected_provider`, filled `providerEvaluations`, and page previews.
4. **Artifact review** – inspect `${STORAGE_ROOT}/ocr_agent/data/output` to ensure reports/logs are emitted as expected.
5. **Performance pass** – if uploads grow large, decide whether to offload `process_document` to a background worker or job queue to avoid long HTTP response times.
6. **Access policies** – confirm the API key logic (`x-ocr-api-key` header) remains compatible with your deployment/authentication story.

"""
유효성 검증 Agent (2단계) - Solar LLM 기반 페이지별 폴백 통합
Solar LLM이 텍스트 추출 결과의 Pass/Fail 판정 및 자동 폴백 반복 (페이지 단위)
"""

import time
from typing import Dict, List, Optional
from datetime import datetime
from itertools import combinations

from ..state import (
    DocumentState, ValidationResult, PageValidationResult, ExtractionResult, PageExtractionResult,
    add_validation_result, add_error
)
from .. import config
from ..utils.llm_client import SolarClient
from ..prompts.validation_prompts import (
    create_validation_prompt,
    parse_validation_response
)


class ValidationAgent:
    """
    2단계: 유효성 검증 에이전트 (Solar LLM 기반 페이지별 폴백 통합)
    
    역할:
    - Solar LLM이 텍스트 추출 결과를 보고 "말이 되는지" 종합 판단
    - 페이지별 Pass/Fail 판정 (1회 LLM 호출)
    - 실패 시 페이지별로 도구 순차 적용:
      1. 단일 도구 시도 → LLM 재검증
      2. Pass가 나오면 즉시 중단
      3. 모두 실패하면 2개 조합 시도 → LLM 재검증
      4. Pass가 나오면 즉시 중단
    
    Solar LLM 검증 기준:
    - 문장의 자연스러움 (말이 되는지)
    - 읽기 순서 (다단 혼입 없음)
    - 불필요한 노이즈 최소화 (헤더/푸터/페이지번호)
    - 표 구조 유지 (표가 있는 경우)
    - 전체적인 가독성 및 실무 사용 가능성
    """
    
    def __init__(self):
        self.llm_client = SolarClient()
        self._init_tools()
    
    def _init_tools(self):
        """폴백 도구 초기화"""
        try:
            from ..tools.custom_split_tool import CustomSplitTool
            from ..tools.layout_parser_tool import LayoutParserTool
            from ..tools.table_enhancement_tool import TableEnhancementTool
            
            self.tools = {
                "custom_split": CustomSplitTool(),
                "layout_reorder": LayoutParserTool(),
                "table_enhancement": TableEnhancementTool()
            }
            print("[OK] Fallback tools initialized (3 tools)")
        except Exception as e:
            print(f"[WARNING] Some tools failed to initialize: {e}")
            self.tools = {}
    
    def run(self, state: DocumentState) -> DocumentState:
        """유효성 검증 실행 (페이지별 + 폴백 통합)"""
        
        print(f"\n{'='*60}")
        print(f"[VALIDATION] Starting validation with page-level fallback")
        print(f"{'='*60}\n")
        
        extraction_results = state["extraction_results"]
        
        for idx, extraction in enumerate(extraction_results, 1):
            if extraction.status != "success":
                print(f"[SKIP] [{idx}/{len(extraction_results)}] {extraction.strategy} - extraction failed")
                continue
            
            print(f"\n[{idx}/{len(extraction_results)}] Validating {extraction.strategy}...")
            print(f"  Sampled pages: {extraction.sampled_pages}")
            
            # 페이지별 검증 + 폴백
            page_validations = []
            for page_idx, page_result in enumerate(extraction.page_results, 1):
                print(f"\n  [{page_idx}/{len(extraction.page_results)}] Page {page_result.page_num}...")
                
                # 페이지 검증 (폴백 포함)
                page_validation = self._validate_page_with_fallback(
                    page_result, extraction, state
                )
                
                if page_validation:
                    page_validations.append(page_validation)
                    
                    # 결과 출력
                    if page_validation.passed:
                        fallback_info = f" (after {len(page_validation.fallback_path)} tools)" if page_validation.fallback_path else ""
                        print(f"    [PASS]{fallback_info} scores: {page_validation.scores}")
                    else:
                        print(f"    [FAIL] after {page_validation.fallback_attempts} attempts")
                        print(f"    Failed axes: {[k for k, v in page_validation.pass_flags.items() if not v]}")
                        print(f"    Final scores: {page_validation.scores}")
                else:
                    print(f"    [ERROR] Validation failed")
            
            # 전체 검증 결과 생성 (페이지별 평균)
            if page_validations:
                validation = self._aggregate_page_validations(extraction, page_validations)
                state = add_validation_result(state, validation)
                
                passed_pages = sum(1 for pv in page_validations if pv.passed)
                print(f"\n  Summary: {passed_pages}/{len(page_validations)} pages passed")
                print(f"  Average scores: {validation.scores}")
                
                if not validation.passed:
                    # 실패한 조합 기록
                    state["failed_combinations"].append({
                        "strategy": extraction.strategy,
                        "scores": validation.scores,
                        "pass_flags": validation.pass_flags,
                        "page_pass_rate": passed_pages / len(page_validations),
                        "timestamp": datetime.now().isoformat()
                    })
        
        passed_count = sum(1 for v in state["validation_results"] if v.passed)
        print(f"\n[SUMMARY] Validation results: {passed_count}/{len(state['validation_results'])} strategies passed\n")
        
        return state
    
    def _validate_page_with_fallback(
        self,
        page_result: PageExtractionResult,
        extraction: ExtractionResult,
        state: DocumentState
    ) -> Optional[PageValidationResult]:
        """
        개별 페이지 검증 + 실패 시 폴백 시도
        
        프로세스:
        1. 초기 검증
        2. Pass → 반환
        3. Fail → 단일 도구 순차 시도
        4. Pass → 반환
        5. 모두 Fail → 2개 조합 시도
        6. Pass → 반환
        7. 모두 Fail → 최종 Fail 반환
        """
        
        # 1. 초기 검증
        print(f"    Initial validation...", end=" ")
        page_validation = self._validate_page(page_result, extraction)
        
        if not page_validation:
            return None
        
        if page_validation.passed:
            print("[PASS]")
            return page_validation
        
        print(f"[FAIL]")
        print(f"    Failed axes: {[k for k, v in page_validation.pass_flags.items() if not v]}")
        print(f"    Scores: {page_validation.scores}")
        
        # 2. 도구 조합 시도 (단일 → 2개)
        best_validation = page_validation
        
        tool_combinations = self._generate_tool_combinations(page_validation)
        
        for combo_idx, tool_combo in enumerate(tool_combinations, 1):
            print(f"    Trying tools: {' + '.join(tool_combo)}...", end=" ")
            
            # 도구 적용
            improved_page = self._apply_tools_to_page(
                page_result,
                tool_combo,
                state["document_path"]
            )
            
            if not improved_page:
                print("[SKIP]")
                continue
            
            # 재검증
            new_validation = self._revalidate_page(
                improved_page,
                extraction,
                previous_validation=best_validation,
                fallback_tools=tool_combo
            )
            
            if not new_validation:
                print("[ERROR]")
                continue
            
            # Pass 체크
            if new_validation.passed:
                print(f"[PASS] (confidence: {new_validation.scores.get('llm_confidence', 0):.2f})")
                return new_validation
            else:
                # Fail - confidence 비교해서 최선 유지
                old_confidence = best_validation.scores.get('llm_confidence', 0)
                new_confidence = new_validation.scores.get('llm_confidence', 0)
                
                print(f"[FAIL] (confidence: {new_confidence:.2f})")
                
                # confidence가 개선되면 best 업데이트
                if new_confidence > old_confidence:
                    best_validation = new_validation
                    print(f"    [IMPROVEMENT] {old_confidence:.2f} → {new_confidence:.2f}")
                
                # confidence가 전혀 개선 안 되면 조기 중단 (2회 시도 후)
                if new_confidence <= old_confidence and combo_idx > 2:
                    print(f"    [STOP] No improvement, stopping fallback")
                    break
        
        # 최종 Fail (최선의 결과 반환)
        return best_validation
    
    def _validate_page(
        self,
        page_result: PageExtractionResult,
        extraction: ExtractionResult
    ) -> Optional[PageValidationResult]:
        """개별 페이지 검증 (Solar LLM 기반)"""
        
        start_time = time.time()
        
        try:
            # 텍스트가 너무 짧으면 즉시 Fail
            if len(page_result.text.strip()) < 20:
                return PageValidationResult(
                    page_num=page_result.page_num,
                    extraction_id=extraction.strategy,
                    strategy=extraction.strategy,
                    passed=False,
                    scores={"llm_confidence": 0.0},
                    pass_flags={"overall": False},
                    fallback_path=[],
                    fallback_attempts=0,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    status="fail",
                    metadata={"fail_reason": "text_too_short"}
                )
            
            # Validation 프롬프트 생성
            has_tables = len(page_result.tables) > 0
            table_preview = ""
            if has_tables and page_result.tables:
                first_table = page_result.tables[0]
                table_preview = f"행: {first_table.get('rows', 0)}, 열: {first_table.get('cols', 0)}"
            
            prompt = create_validation_prompt(
                page_text=page_result.text,
                page_num=page_result.page_num,
                strategy=extraction.strategy,
                has_tables=has_tables,
                table_preview=table_preview
            )
            
            # Solar LLM 호출
            print(f"      [LLM] Calling Solar for validation...", end=" ")
            response = self.llm_client.call(prompt)
            
            if not response:
                print("[ERROR]")
                return None
            
            # 응답 파싱
            result = parse_validation_response(response["content"])
            
            passed = result['pass']
            confidence = result['confidence']
            reason = result['reason']
            issues = result['issues']
            suggestions = result['suggestions']
            
            print(f"{'[PASS]' if passed else '[FAIL]'} (confidence: {confidence:.2f})")
            
            # 점수 형태로 변환 (하위 호환성)
            scores = {
                "llm_confidence": confidence,
                "overall": 1.0 if passed else 0.0
            }
            
            pass_flags = {
                "overall": passed
            }
            
            processing_time = (time.time() - start_time) * 1000  # ms
            
            return PageValidationResult(
                page_num=page_result.page_num,
                extraction_id=extraction.strategy,
                strategy=extraction.strategy,
                passed=passed,
                scores=scores,
                pass_flags=pass_flags,
                fallback_path=[],
                fallback_attempts=0,
                processing_time_ms=processing_time,
                status="pass" if passed else "fail",
                metadata={
                    "llm_reason": reason,
                    "llm_issues": issues,
                    "llm_suggestions": suggestions,
                    "llm_confidence": confidence,
                    "page_text": page_result.text  # 2단 레이아웃 감지용
                }
            )
            
        except Exception as e:
            print(f"[ERROR] Page validation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _apply_custom_split_and_reextract(
        self,
        page_result: PageExtractionResult,
        document_path: str
    ) -> Optional[PageExtractionResult]:
        """
        Custom Split으로 PDF 전처리 후 1단계 도구로 재추출
        
        Args:
            page_result: 원본 페이지 결과
            document_path: 문서 경로
            
        Returns:
            재추출된 페이지 결과 또는 None
        """
        try:
            from pathlib import Path
            
            print(f"      [CUSTOM_SPLIT] Preprocessing PDF...")
            
            # PDF 전처리
            pdf_path = Path(document_path)
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            # Custom Split 적용
            custom_split_tool = self.tools["custom_split"]
            split_pdf_bytes = custom_split_tool._process_pdf_bytes(pdf_bytes)
            
            # 임시 파일로 저장
            temp_dir = config.EXTRACTED_DIR / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_pdf_path = temp_dir / f"{pdf_path.stem}_split_{page_result.page_num}.pdf"
            
            with open(temp_pdf_path, 'wb') as f:
                f.write(split_pdf_bytes)
            
            print(f"      [CUSTOM_SPLIT] PDF preprocessed, re-extracting with {page_result.strategy}...")
            
            # 1단계 도구로 재추출
            if page_result.strategy == "pdfplumber":
                from ..tools.pdfplumber_tool import PDFPlumberTool
                extraction_tool = PDFPlumberTool()
            elif page_result.strategy == "pdfminer":
                from ..tools.pdfminer_tool import PDFMinerTool
                extraction_tool = PDFMinerTool()
            elif page_result.strategy == "pypdfium2":
                from ..tools.pypdfium2_tool import PyPDFium2Tool
                extraction_tool = PyPDFium2Tool()
            else:
                print(f"      [ERROR] Unknown extraction strategy: {page_result.strategy}")
                return None
            
            # 재추출
            result = extraction_tool.extract(temp_pdf_path)
            
            # 해당 페이지 찾기 (페이지 번호가 변경되었을 수 있음)
            # 원본 페이지 번호에 해당하는 페이지를 찾거나, 첫 번째 페이지 사용
            target_page = None
            if result["pages"]:
                # 페이지 수가 증가했을 수 있으므로, 원본 페이지 번호의 2배 근처를 찾음
                for page_data in result["pages"]:
                    if page_data["page"] == page_result.page_num:
                        target_page = page_data
                        break
                
                # 못 찾으면 첫 번째 페이지 사용
                if not target_page:
                    target_page = result["pages"][0]
            
            if not target_page:
                print(f"      [ERROR] No pages found after re-extraction")
                return None
            
            # PageExtractionResult로 변환
            improved_page = PageExtractionResult(
                page_num=page_result.page_num,
                strategy=page_result.strategy + "+custom_split",
                text=target_page["text"],
                bbox=target_page.get("bbox", []),
                tables=target_page.get("tables", []),
                processing_time_ms=0.0,
                status="success",
                metadata={
                    "preprocessed_with": "custom_split",
                    "original_strategy": page_result.strategy
                }
            )
            
            return improved_page
            
        except Exception as e:
            print(f"      [ERROR] Custom split and re-extract failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_tool_combinations(
        self,
        page_validation: PageValidationResult
    ) -> List[List[str]]:
        """
        도구 조합 생성 (LLM 제안 기반)
        
        1. LLM이 제안한 도구 우선 시도
        2. 나머지 도구들 순차 시도
        3. 2개 조합 시도
        
        Note: custom_split은 1단계에서 자동 처리됨
        """
        
        priority_tools = []
        
        # 1. LLM이 제안한 도구 (suggestions에서 추출)
        # (custom_split은 이제 1단계에서 자동 처리됨)
        suggestions = page_validation.metadata.get("llm_suggestions", [])
        
        # 도구 이름 매핑 (LLM 텍스트 → 실제 도구 이름)
        tool_mapping = {
            "custom_split": "custom_split",
            "split": "custom_split",
            "좌우": "custom_split",
            "분할": "custom_split",
            "layout": "layout_reorder",
            "layout_reorder": "layout_reorder",
            "레이아웃": "layout_reorder",
            "table": "table_enhancement",
            "table_enhancement": "table_enhancement",
            "표": "table_enhancement"
        }
        
        for suggestion in suggestions:
            suggestion_lower = suggestion.lower()
            for key, tool_name in tool_mapping.items():
                if key in suggestion_lower and tool_name not in priority_tools:
                    priority_tools.append(tool_name)
                    break
        
        # 2. LLM 제안이 없거나 부족하면 기본 우선순위 사용
        if len(priority_tools) < 3:
            for tool in config.FALLBACK_PRIORITY:
                if tool not in priority_tools and tool in self.tools:
                    priority_tools.append(tool)
        
        # 조합 생성
        combinations_list = []
        
        # 단일 도구 (최대 5개)
        for tool in priority_tools[:5]:
            if tool in self.tools:
                combinations_list.append([tool])
        
        # 2개 조합 (최대 10개)
        if len(priority_tools) >= 2:
            available_tools = [t for t in priority_tools[:4] if t in self.tools]
            for combo in combinations(available_tools, 2):
                combinations_list.append(list(combo))
                if len(combinations_list) >= 15:  # 단일 5개 + 조합 10개
                    break
        
        return combinations_list
    
    def _apply_tools_to_page(
        self,
        page_result: PageExtractionResult,
        tool_names: List[str],
        document_path: str
    ) -> Optional[PageExtractionResult]:
        """
        페이지에 도구 조합 적용
        
        Args:
            page_result: 원본 페이지 결과
            tool_names: 적용할 도구 이름 리스트
            document_path: 문서 경로
            
        Returns:
            개선된 페이지 결과 또는 None
        """
        
        try:
            # custom_split이 포함되어 있으면 특별 처리
            if "custom_split" in tool_names:
                return self._apply_custom_split_and_reextract(
                    page_result, document_path
                )
            
            # 페이지 데이터를 도구가 이해하는 형태로 변환
            page_data = {
                "page": page_result.page_num,
                "text": page_result.text,
                "bbox": page_result.bbox,
                "tables": page_result.tables,
                "source": page_result.strategy
            }
            
            improved_pages = [page_data]
            
            # 도구 순차 적용
            for tool_name in tool_names:
                if tool_name not in self.tools:
                    print(f"[WARNING] Tool {tool_name} not available")
                    continue
                
                tool = self.tools[tool_name]
                
                try:
                    # 도구 적용
                    improved_pages = tool.process(improved_pages, document_path)
                    
                    if not improved_pages:
                        print(f"[WARNING] Tool {tool_name} returned empty result")
                        return None
                    
                except Exception as e:
                    print(f"[ERROR] Tool {tool_name} failed: {e}")
                    return None
            
            # 첫 번째 페이지를 PageExtractionResult로 변환
            if improved_pages:
                improved = improved_pages[0]
                
                return PageExtractionResult(
                    page_num=page_result.page_num,
                    strategy=f"{page_result.strategy}+{'+'.join(tool_names)}",
                    text=improved.get("text", ""),
                    bbox=improved.get("bbox", []),
                    tables=improved.get("tables", []),
                    processing_time_ms=page_result.processing_time_ms,
                    status="success"
                )
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Failed to apply tools: {e}")
            return None
    
    def _revalidate_page(
        self,
        improved_page: PageExtractionResult,
        extraction: ExtractionResult,
        previous_validation: PageValidationResult,
        fallback_tools: List[str]
    ) -> Optional[PageValidationResult]:
        """도구 적용 후 재검증"""
        
        new_validation = self._validate_page(improved_page, extraction)
        
        if new_validation:
            # 폴백 정보 업데이트
            new_validation.fallback_path = previous_validation.fallback_path + fallback_tools
            new_validation.fallback_attempts = previous_validation.fallback_attempts + 1
            new_validation.strategy = improved_page.strategy
        
        return new_validation
    
    def _aggregate_page_validations(
        self,
        extraction: ExtractionResult,
        page_validations: List[PageValidationResult]
    ) -> ValidationResult:
        """페이지별 검증 결과를 집계 (LLM 기반)"""
        
        # LLM confidence 평균 계산
        confidences = [pv.scores.get('llm_confidence', 0.0) for pv in page_validations]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # 전체 통과 여부: 모든 페이지가 통과해야 함
        overall_passed = all(pv.passed for pv in page_validations)
        
        # 평균 처리 시간
        avg_processing_time = sum(pv.processing_time_ms for pv in page_validations) / len(page_validations)
        
        # 폴백 정보 집계
        all_fallback_paths = []
        total_attempts = 0
        for pv in page_validations:
            if pv.fallback_path:
                all_fallback_paths.extend(pv.fallback_path)
            total_attempts += pv.fallback_attempts
        
        # 가장 많이 사용된 도구들을 fallback_path로
        unique_tools = list(set(all_fallback_paths))
        
        return ValidationResult(
            extraction_id=extraction.strategy,
            strategy=extraction.strategy,
            passed=overall_passed,
            page_validations=page_validations,
            scores={
                "llm_confidence": avg_confidence,
                "overall": 1.0 if overall_passed else 0.0
            },
            pass_flags={
                "overall": overall_passed
            },
            fallback_path=unique_tools,
            fallback_attempts=total_attempts,
            pages_text_path=extraction.pages_text_path,
            processing_time_ms=avg_processing_time,
            status="pass" if overall_passed else "fail",
            metadata={
                "extraction_time_ms": extraction.processing_time_ms,
                "page_count": len(page_validations),
                "total_page_count": extraction.total_page_count,
                "pages_with_fallback": sum(1 for pv in page_validations if pv.fallback_path),
                "avg_llm_confidence": avg_confidence
            }
        )


# ===== 하위 호환성을 위한 FallbackHandler (Deprecated) =====
class FallbackHandler:
    """
    [DEPRECATED] 이제 ValidationAgent 내부에서 페이지별로 처리됨
    
    하위 호환성을 위해 유지하지만 실제로는 사용되지 않음
    """
    
    def __init__(self):
        print("[WARNING] FallbackHandler is deprecated. Fallback is now handled by ValidationAgent.")
    
    def run(self, state: DocumentState) -> DocumentState:
        """더미 실행 - 아무것도 하지 않음"""
        print("[INFO] FallbackHandler.run() called but skipped (handled by ValidationAgent)")
        return state


if __name__ == "__main__":
    # 테스트
    print("[OK] ValidationAgent module loaded (with integrated page-level fallback)")

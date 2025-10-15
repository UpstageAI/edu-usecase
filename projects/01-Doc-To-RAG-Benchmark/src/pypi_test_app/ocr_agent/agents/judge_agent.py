"""
LLM Judge Agent (3단계)
Solar pro2 기반 품질 평가 및 최적 전략 선택
"""

import time
from typing import Dict, List, Optional

from ..state import (
    DocumentState, JudgeResult, PageJudgeResult, FinalSelection, ValidationResult, PageValidationResult,
    add_judge_result, set_final_selection
)
from .. import config
from ..utils.llm_client import SolarClient
from ..prompts.judge_prompts import (
    create_judge_prompt,
    parse_judge_response
)


class JudgeAgent:
    """
    3단계: LLM Judge 에이전트
    
    역할:
    - Pass된 버전들을 Solar pro2로 점수화
    - 평가 축: S_read, S_sent, S_noise, S_table, S_fig → S_total
    - 속도·비용 고려하여 최적 전략 선택
    """
    
    def __init__(self):
        self.llm_client = SolarClient()
    
    def run(self, state: DocumentState) -> DocumentState:
        """LLM Judge 실행 (페이지별)"""
        
        print(f"\n{'='*60}")
        print(f"[JUDGE] Starting LLM Judge evaluation (page-by-page)")
        print(f"{'='*60}\n")
        
        # 모든 validation을 확인 (페이지 중 하나라도 Pass면 평가)
        validation_results = state["validation_results"]
        
        # 페이지 중 하나라도 Pass한 validation만 선택
        candidates = [v for v in validation_results 
                      if any(p.passed for p in v.page_validations)]
        
        if not candidates:
            print("[WARNING] No pages passed validation")
            return state
        
        print(f"[INFO] Evaluating {len(candidates)} strategies")
        total_passed_pages = sum(sum(1 for p in v.page_validations if p.passed) for v in candidates)
        print(f"[INFO] Total passed pages to judge: {total_passed_pages}\n")
        
        # 각 후보 평가 (페이지별)
        for idx, validation in enumerate(candidates, 1):
            print(f"[{idx}/{len(candidates)}] Evaluating {validation.strategy}...")
            print(f"  Pages: {len(validation.page_validations)}")
            
            # 페이지별 Judge 실행 (Pass된 페이지만)
            page_judges = []
            for page_val in validation.page_validations:
                if page_val.passed:  # Pass된 페이지만 LLM Judge
                    print(f"  Page {page_val.page_num}...", end=" ")
                    page_judge = self._judge_page(page_val, validation, state)
                    if page_judge:
                        page_judges.append(page_judge)
                        print(f"S_total={page_judge.S_total:.2f}")
                    else:
                        print("[ERROR]")
            
            # 전체 Judge 결과 생성 (페이지별 평균)
            if page_judges:
                judge_result = self._aggregate_page_judges(validation, page_judges)
                state = add_judge_result(state, judge_result)
                
                print(f"\n  [OK] Average S_total: {judge_result.S_total:.3f} ({judge_result.grade})")
                print(f"  Detail: read={judge_result.S_read:.2f}, sent={judge_result.S_sent:.2f}, "
                      f"noise={judge_result.S_noise:.2f}, table={judge_result.S_table:.2f}, "
                      f"fig={judge_result.S_fig:.2f}")
                print(f"  Speed: {judge_result.ocr_speed_ms_per_page:.0f}ms/page\n")
            else:
                print(f"  [WARNING] No pages passed LLM Judge\n")
        
        # 최종 전략 선택
        if state["judge_results"]:
            final_selection = self._select_best_strategy(state)
            state = set_final_selection(state, final_selection)
            
            print(f"\n[FINAL] Selected strategy: {final_selection.selected_strategy}")
            print(f"   Score: {final_selection.S_total:.3f}")
            print(f"   Rationale: {final_selection.selection_rationale}\n")
        else:
            print(f"\n[WARNING] No selectable strategy\n")
        
        return state
    
    def _judge_page(
        self,
        page_validation: PageValidationResult,
        validation: ValidationResult,
        state: DocumentState
    ) -> Optional[PageJudgeResult]:
        """개별 페이지 Judge 평가"""
        
        start_time = time.time()
        
        try:
            # 페이지 데이터 생성
            # validation에서 해당 페이지 찾기
            extraction = next((e for e in state["extraction_results"] if e.strategy == validation.strategy), None)
            if not extraction:
                return None
            
            page_result = next((p for p in extraction.page_results if p.page_num == page_validation.page_num), None)
            if not page_result:
                return None
            
            page_data = {
                "page": page_result.page_num,
                "text": page_result.text,
                "bbox": page_result.bbox,
                "tables": page_result.tables
            }
            
            # Judge 프롬프트 생성 (단일 페이지)
            prompt = create_judge_prompt(
                strategy=validation.strategy,
                pages=[page_data],
                doc_meta=state["doc_meta"]
            )
            
            # LLM 호출
            response = self.llm_client.call(prompt)
            
            if not response:
                return None
            
            # 응답 파싱
            scores = parse_judge_response(response["content"])
            
            # 가중 합산
            S_total = sum(
                scores[key] * config.JUDGE_WEIGHTS[key]
                for key in config.JUDGE_WEIGHTS.keys()
            )
            
            # 등급 판정
            if S_total >= config.SCORE_THRESHOLDS["pass"]:
                grade = "pass"
            elif S_total >= config.SCORE_THRESHOLDS["borderline"]:
                grade = "borderline"
            else:
                grade = "fail"
            
            return PageJudgeResult(
                page_num=page_validation.page_num,
                validation_id=validation.strategy,
                strategy=validation.strategy,
                S_read=scores["S_read"],
                S_sent=scores["S_sent"],
                S_noise=scores["S_noise"],
                S_table=scores["S_table"],
                S_fig=scores["S_fig"],
                S_total=S_total,
                grade=grade,
                rationale=response.get("rationale", ""),
                comments=response.get("comments", {}),
                metadata={}
            )
            
        except Exception as e:
            print(f"[ERROR] Page judge error: {str(e)}")
            return None
    
    def _aggregate_page_judges(
        self,
        validation: ValidationResult,
        page_judges: List[PageJudgeResult]
    ) -> JudgeResult:
        """페이지별 Judge 결과를 집계"""
        
        # 각 점수별 평균 계산
        avg_scores = {
            "S_read": sum(pj.S_read for pj in page_judges) / len(page_judges),
            "S_sent": sum(pj.S_sent for pj in page_judges) / len(page_judges),
            "S_noise": sum(pj.S_noise for pj in page_judges) / len(page_judges),
            "S_table": sum(pj.S_table for pj in page_judges) / len(page_judges),
            "S_fig": sum(pj.S_fig for pj in page_judges) / len(page_judges),
        }
        
        # S_total 평균
        avg_S_total = sum(pj.S_total for pj in page_judges) / len(page_judges)
        
        # 등급 판정 (평균 기준)
        if avg_S_total >= config.SCORE_THRESHOLDS["pass"]:
            grade = "pass"
        elif avg_S_total >= config.SCORE_THRESHOLDS["borderline"]:
            grade = "borderline"
        else:
            grade = "fail"
        
        # 속도 계산 (ms/page)
        total_time_ms = validation.metadata.get("extraction_time_ms", 0) + validation.processing_time_ms
        page_count = validation.metadata.get("page_count", 1)
        speed_per_page = total_time_ms / max(page_count, 1)
        
        return JudgeResult(
            validation_id=validation.strategy,
            strategy=validation.strategy,
            page_judges=page_judges,
            S_read=avg_scores["S_read"],
            S_sent=avg_scores["S_sent"],
            S_noise=avg_scores["S_noise"],
            S_table=avg_scores["S_table"],
            S_fig=avg_scores["S_fig"],
            S_total=avg_S_total,
            grade=grade,
            ocr_speed_ms_per_page=speed_per_page,
            rationale=f"Average of {len(page_judges)} pages",
            comments={},
            metadata={
                "page_judge_count": len(page_judges),
                "fallback_path": validation.fallback_path
            }
        )
    
    def _select_sample_pages(self, pages: List[Dict], max_pages: int = 5) -> List[Dict]:
        """비용 절감을 위한 샘플 페이지 선택"""
        
        if len(pages) <= max_pages:
            return pages
        
        # 첫 페이지, 중간 페이지들, 마지막 페이지 선택
        indices = [0]  # 첫 페이지
        
        # 중간 페이지들 균등 샘플링
        step = (len(pages) - 1) / (max_pages - 2)
        for i in range(1, max_pages - 1):
            idx = int(i * step)
            if idx not in indices:
                indices.append(idx)
        
        indices.append(len(pages) - 1)  # 마지막 페이지
        
        return [pages[i] for i in sorted(indices)]
    
    def _select_best_strategy(self, state: DocumentState) -> FinalSelection:
        """최적 전략 선택"""
        
        judge_results = state["judge_results"]
        
        # Pass 등급만 필터링
        pass_results = [r for r in judge_results if r.grade == "pass"]
        
        if not pass_results:
            # Pass 없으면 Borderline 중 최고점
            borderline_results = [r for r in judge_results if r.grade == "borderline"]
            if borderline_results:
                pass_results = borderline_results
            else:
                # 그마저도 없으면 전체 중 최고점
                pass_results = judge_results
        
        # 복합 점수 계산: 품질 + 속도
        def calculate_composite_score(result: JudgeResult) -> float:
            # 품질 점수 (0-100을 0-1로 정규화)
            quality_score = result.S_total / 100.0
            
            # 속도 점수 (빠를수록 높음, 0~1 정규화)
            # 1500ms/page를 기준으로 정규화
            speed_score = max(0, 1 - (result.ocr_speed_ms_per_page / 1500))
            
            # 가중 합산 (품질 80%, 속도 20%)
            composite = (
                quality_score * config.SELECTION_WEIGHTS["score"] +
                speed_score * config.SELECTION_WEIGHTS["speed"]
            )
            
            return composite
        
        # 최고 점수 선택
        best_result = max(pass_results, key=calculate_composite_score)
        
        # 선정 근거 생성
        rationale = (
            f"S_total {best_result.S_total:.1f}/100으로 최고 품질. "
            f"처리 속도 {best_result.ocr_speed_ms_per_page:.0f}ms/page. "
        )
        
        # 동률 비교 (2점 이내 차이는 동률로 간주)
        same_score_results = [r for r in pass_results if abs(r.S_total - best_result.S_total) < 2.0]
        if len(same_score_results) > 1:
            fastest = min(same_score_results, key=lambda r: r.ocr_speed_ms_per_page)
            if fastest.strategy == best_result.strategy:
                rationale += "동점 중 가장 빠른 전략."
        
        return FinalSelection(
            document_name=state["document_name"],
            selected_strategy=best_result.strategy,
            S_total=best_result.S_total,
            ocr_speed_ms_per_page=best_result.ocr_speed_ms_per_page,
            selection_rationale=rationale,
            metadata={
                "total_candidates": len(judge_results),
                "pass_count": len([r for r in judge_results if r.grade == "pass"]),
                "composite_score": calculate_composite_score(best_result)
            }
        )


if __name__ == "__main__":
    # 테스트
    print("[OK] JudgeAgent module loaded")


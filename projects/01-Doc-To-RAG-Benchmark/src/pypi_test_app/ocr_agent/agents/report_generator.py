"""
리포트 생성 Agent
최종 결과를 다양한 형식의 리포트로 생성
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from ..state import DocumentState, JudgeResult
from .. import config

# 세션 타임스탬프 (모든 CSV가 같은 타임스탬프 사용)
SESSION_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


class ReportGenerator:
    """
    리포트 생성 에이전트
    
    역할:
    - judge_report.json 생성 (상세 정보)
    - full_combinations.csv (모든 조합)
    - final_selection.csv (최종 선택)
    - failed_documents.csv (실패 문서)
    """
    
    def __init__(self):
        pass
    
    def run(self, state: DocumentState) -> DocumentState:
        """리포트 생성 실행"""
        
        print(f"\n{'='*60}")
        print(f"[REPORT] Starting report generation")
        print(f"{'='*60}\n")
        
        document_name = state["document_name"]
        
        # 1. judge_report.json 생성
        print("[1/5] Generating judge_report.json...")
        self._generate_judge_report(state)
        print("[OK] Complete")
        
        # 2. page_level_results.csv 업데이트 (페이지별 상세)
        print("\n[2/4] Updating page_level_results.csv...")
        self._update_page_level_csv(state)
        print("[OK] Complete")
        
        # 3. final_selection.csv 업데이트
        print("\n[3/4] Updating final_selection.csv...")
        self._update_final_selection_csv(state)
        print("[OK] Complete")
        
        # 4. failed_documents.csv 업데이트 (필요 시)
        if not state["final_selection"] or not state["judge_results"]:
            print("\n[4/4] Updating failed_documents.csv...")
            self._update_failed_documents_csv(state)
            print("[OK] Complete")
        else:
            print("\n[SKIP] [4/4] failed_documents.csv not needed (success case)")
        
        print(f"\n[OUTPUT] Reports saved to: {config.REPORTS_DIR}")
        print(f"[OUTPUT] Tables saved to: {config.TABLES_DIR}\n")
        
        return state
    
    def _generate_judge_report(self, state: DocumentState) -> None:
        """상세 judge_report.json 생성"""
        
        report = {
            "document_name": state["document_name"],
            "document_path": state["document_path"],
            "timestamp": datetime.now().isoformat(),
            "doc_meta": state["doc_meta"],
            
            # 추출 결과
            "extraction_results": [
                {
                    "strategy": r.strategy,
                    "status": r.status,
                    "page_count": r.page_count,
                    "total_page_count": r.total_page_count,
                    "sampled_pages": r.sampled_pages,
                    "processing_time_ms": r.processing_time_ms,
                    "error_message": r.error_message,
                    "page_results": [
                        {
                            "page_num": pr.page_num,
                            "text_length": len(pr.text),
                            "text_preview": pr.text[:200] if pr.text else "",
                            "bbox_count": len(pr.bbox),
                            "tables_count": len(pr.tables),
                            "processing_time_ms": pr.processing_time_ms,
                            "status": pr.status
                        }
                        for pr in r.page_results
                    ]
                }
                for r in state["extraction_results"]
            ],
            
            # 검증 결과
            "validation_results": [
                {
                    "strategy": v.strategy,
                    "passed": v.passed,
                    "scores": v.scores,
                    "pass_flags": v.pass_flags,
                    "fallback_path": v.fallback_path,
                    "fallback_attempts": v.fallback_attempts,
                    "improvement_delta": v.improvement_delta,
                    "processing_time_ms": v.processing_time_ms,
                    "page_validations": [
                        {
                            "page_num": pv.page_num,
                            "passed": pv.passed,
                            "scores": pv.scores,
                            "pass_flags": pv.pass_flags,
                            "fallback_path": pv.fallback_path,
                            "processing_time_ms": pv.processing_time_ms
                        }
                        for pv in v.page_validations
                    ]
                }
                for v in state["validation_results"]
            ],
            
            # Judge 결과
            "judge_results": [
                {
                    "strategy": j.strategy,
                    "S_read": j.S_read,
                    "S_sent": j.S_sent,
                    "S_noise": j.S_noise,
                    "S_table": j.S_table,
                    "S_fig": j.S_fig,
                    "S_total": j.S_total,
                    "grade": j.grade,
                    "ocr_speed_ms_per_page": j.ocr_speed_ms_per_page,
                    "rationale": j.rationale,
                    "comments": j.comments,
                    "page_judges": [
                        {
                            "page_num": pj.page_num,
                            "S_read": pj.S_read,
                            "S_sent": pj.S_sent,
                            "S_noise": pj.S_noise,
                            "S_table": pj.S_table,
                            "S_fig": pj.S_fig,
                            "S_total": pj.S_total,
                            "grade": pj.grade
                        }
                        for pj in j.page_judges
                    ]
                }
                for j in state["judge_results"]
            ],
            
            # 최종 선택
            "final_selection": {
                "selected_strategy": state["final_selection"].selected_strategy,
                "S_total": state["final_selection"].S_total,
                "ocr_speed_ms_per_page": state["final_selection"].ocr_speed_ms_per_page,
                "selection_rationale": state["final_selection"].selection_rationale,
                "metadata": state["final_selection"].metadata
            } if state["final_selection"] else None,
            
            # 실패 조합
            "failed_combinations": state["failed_combinations"],
            
            # 에러 로그
            "error_log": state["error_log"],
            
            # 처리 시간
            "start_time": state["start_time"].isoformat(),
            "end_time": datetime.now().isoformat()
        }
        
        # 저장
        report_path = config.REPORTS_DIR / f"{state['document_name']}_judge_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    
    def _update_page_level_csv(self, state: DocumentState) -> None:
        """페이지별 상세 결과 CSV 업데이트"""
        
        csv_path = config.TABLES_DIR / f"page_level_results_{SESSION_TIMESTAMP}.csv"
        
        # 기존 데이터 로드
        existing_rows = []
        if csv_path.exists():
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
        
        # 각 검증 결과에 대해 페이지별 행 추가
        for validation in state["validation_results"]:
            # 해당 추출 결과 찾기
            extraction = next(
                (e for e in state["extraction_results"] if e.strategy == validation.strategy),
                None
            )
            
            if not extraction:
                continue
            
            # 해당 Judge 결과 찾기
            judge_result = next(
                (j for j in state["judge_results"] if j.strategy == validation.strategy),
                None
            )
            
            # 페이지별로 행 생성
            for page_val in validation.page_validations:
                # 해당 페이지의 추출 결과 찾기
                page_extraction = next(
                    (p for p in extraction.page_results if p.page_num == page_val.page_num),
                    None
                )
                
                # 해당 페이지의 Judge 결과 찾기
                page_judge = None
                if judge_result and judge_result.page_judges:
                    page_judge = next(
                        (pj for pj in judge_result.page_judges if pj.page_num == page_val.page_num),
                        None
                    )
                
                # 텍스트 추출 결과 (앞 100자)
                text_preview = ""
                if page_extraction and page_extraction.text:
                    text_preview = page_extraction.text[:100].replace('\n', ' ').strip()
                    if len(page_extraction.text) > 100:
                        text_preview += "..."
                
                # 폴백 경로 (페이지별 또는 전체)
                fallback_sequence = "→".join(page_val.fallback_path) if page_val.fallback_path else \
                                  ("→".join(validation.fallback_path) if validation.fallback_path else "-")
                
                # OCR/전략 컬럼: 페이지별 전략 (폴백 도구 포함)
                # page_val.strategy가 있으면 그것 사용 (폴백 적용된 전략), 없으면 기본 전략
                strategy_with_fallback = page_val.strategy if hasattr(page_val, 'strategy') and page_val.strategy else validation.strategy
                
                # 폴백 경로가 있으면 전략명에 추가
                if page_val.fallback_path:
                    strategy_with_fallback = validation.strategy + "+" + "+".join(page_val.fallback_path)
                
                # 페이지당 비용 계산
                page_cost = extraction.extraction_cost_usd / len(extraction.page_results) if extraction.page_results else 0.0
                
                row = {
                    "파일 이름": state["document_name"],
                    "페이지 번호": page_val.page_num,
                    "OCR/전략": strategy_with_fallback,
                    "텍스트 미리보기": text_preview,
                    "유효성 Pass": "✅" if page_val.passed else "❌",
                    "S_read": f"{page_judge.S_read:.2f}" if page_judge else "-",
                    "S_sent": f"{page_judge.S_sent:.2f}" if page_judge else "-",
                    "S_noise": f"{page_judge.S_noise:.2f}" if page_judge else "-",
                    "S_table": f"{page_judge.S_table:.2f}" if page_judge else "-",
                    "S_total": f"{page_judge.S_total:.2f}" if page_judge else "-",
                    "처리 시간(ms)": f"{page_extraction.processing_time_ms:.1f}" if page_extraction else "-",
                    "추출 비용(USD)": f"${page_cost:.4f}" if page_cost > 0 else "$0.0000",
                    "폴백 경로": fallback_sequence,
                    "페이지별 최선 선택": "0"  # 나중에 _mark_best_page_combinations에서 업데이트
                }
                
                existing_rows.append(row)
        
        # 페이지별 최선 조합 선택 (S_total 최고 → 처리시간 최저)
        self._mark_best_page_combinations(existing_rows)
        
        # CSV 저장
        fieldnames = [
            "파일 이름", "페이지 번호", "OCR/전략", "텍스트 미리보기", 
            "유효성 Pass", "S_read", "S_sent", "S_noise", "S_table", "S_total",
            "처리 시간(ms)", "추출 비용(USD)", "폴백 경로", "페이지별 최선 선택"
        ]
        
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)
    
    def _mark_best_page_combinations(self, rows: List[Dict[str, Any]]) -> None:
        """
        페이지별로 최선의 조합을 선택하여 표시
        
        선택 기준:
        1. 같은 파일명 + 같은 페이지 번호로 그룹화
        2. S_total이 가장 높은 것 선택
        3. S_total 동점 시 처리 시간이 가장 짧은 것 선택
        4. 선택된 조합: "페이지별 최선 선택" = "1"
        5. 나머지 조합: "페이지별 최선 선택" = "0"
        """
        from collections import defaultdict
        
        # 파일명 + 페이지 번호별로 그룹화
        page_groups = defaultdict(list)
        for row in rows:
            key = (row["파일 이름"], row["페이지 번호"])
            page_groups[key].append(row)
        
        # 각 그룹에서 최선 조합 선택
        for key, group in page_groups.items():
            # S_total과 처리시간으로 정렬
            # S_total이 "-"인 경우 (fail)는 -1로 처리
            def get_sort_key(row):
                try:
                    s_total = float(row.get("S_total", "-1")) if row.get("S_total", "-") != "-" else -1
                except:
                    s_total = -1
                
                try:
                    time_ms = float(row.get("처리 시간(ms)", "999999"))
                except:
                    time_ms = 999999
                
                # S_total 높은 순 (내림차순), 처리시간 짧은 순 (오름차순)
                return (-s_total, time_ms)
            
            sorted_group = sorted(group, key=get_sort_key)
            
            # 최선 조합 (첫 번째)에만 1 표시
            for i, row in enumerate(sorted_group):
                row["페이지별 최선 선택"] = "1" if i == 0 else "0"
    
    def _update_full_combinations_csv(self, state: DocumentState) -> None:
        """전체 조합 CSV 업데이트 (사용 안 함 - 주석 처리됨)"""
        return  # 이 리포트는 생성하지 않음
        
        csv_path = config.TABLES_DIR / f"full_combinations_{SESSION_TIMESTAMP}.csv"
        
        # 기존 데이터 로드
        existing_rows = []
        if csv_path.exists():
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
        
        # 새 행 추가
        for validation in state["validation_results"]:
            # 해당 validation의 judge 결과 찾기
            judge_result = next(
                (j for j in state["judge_results"] if j.strategy == validation.strategy),
                None
            )
            
            # 최종 선택 여부
            is_final_selection = (
                state["final_selection"] and 
                state["final_selection"].selected_strategy == validation.strategy
            )
            
            row = {
                "파일 이름": state["document_name"],
                "OCR/전략": validation.strategy,
                "유효성 Pass": "✅" if validation.passed else "❌",
                "S_read": f"{judge_result.S_read:.2f}" if judge_result else "-",
                "S_sent": f"{judge_result.S_sent:.2f}" if judge_result else "-",
                "S_noise": f"{judge_result.S_noise:.2f}" if judge_result else "-",
                "S_table": f"{judge_result.S_table:.2f}" if judge_result else "-",
                "S_total": f"{judge_result.S_total:.2f}" if judge_result else "-",
                "OCR 속도(ms/쪽)": f"{judge_result.ocr_speed_ms_per_page:.0f}" if judge_result else "-",
                "폴백 경로": "→".join(validation.fallback_path) if validation.fallback_path else "-",
                "비고": judge_result.rationale[:50] + "..." if judge_result and len(judge_result.rationale) > 50 else (judge_result.rationale if judge_result else ""),
                "문서별 최종 선택": "1" if is_final_selection else "0"
            }
            
            existing_rows.append(row)
        
        # CSV 저장
        fieldnames = [
            "파일 이름", "OCR/전략", "유효성 Pass", "S_read", "S_sent", "S_noise", 
            "S_table", "S_total", "OCR 속도(ms/쪽)", "폴백 경로", "비고", "문서별 최종 선택"
        ]
        
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)
    
    def _update_final_selection_csv(self, state: DocumentState) -> None:
        """최종 선택 CSV 업데이트"""
        
        if not state["final_selection"]:
            return
        
        csv_path = config.TABLES_DIR / f"final_selection_{SESSION_TIMESTAMP}.csv"
        
        # 기존 데이터 로드
        existing_rows = []
        if csv_path.exists():
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                existing_rows = [row for row in reader if row["파일 이름"] != state["document_name"]]
        
        selection = state["final_selection"]

        # 추출 비용 찾기
        extraction_result = next(
            (e for e in state["extraction_results"] if e.strategy == selection.selected_strategy),
            None
        )
        total_cost = extraction_result.extraction_cost_usd if extraction_result else 0.0
        
        # 새 행 추가
        row = {
            "파일 이름": state["document_name"],
            "최종 선정 전략": selection.selected_strategy,
            "S_total": f"{selection.S_total:.2f}",
            "OCR 속도(ms/쪽)": f"{selection.ocr_speed_ms_per_page:.0f}",
            "추출 비용(USD)": f"${total_cost:.4f}",
            "선정 근거": selection.selection_rationale
        }
        
        existing_rows.append(row)
        
        # CSV 저장
        fieldnames = ["파일 이름", "최종 선정 전략", "S_total", "OCR 속도(ms/쪽)", "추출 비용(USD)", "선정 근거"]
        
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)
    
    def _update_failed_documents_csv(self, state: DocumentState) -> None:
        """실패 문서 CSV 업데이트"""
        
        csv_path = config.TABLES_DIR / f"failed_documents_{SESSION_TIMESTAMP}.csv"
        
        # 기존 데이터 로드
        existing_rows = []
        if csv_path.exists():
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                existing_rows = [row for row in reader if row["파일 이름"] != state["document_name"]]
        
        # 실패 이유 분석
        failure_reasons = []
        
        if not state["extraction_results"]:
            failure_reasons.append("기본 추출 실패")
        elif not state["validation_results"]:
            failure_reasons.append("유효성 검증 실패")
        elif not any(v.passed for v in state["validation_results"]):
            # 모든 검증 실패
            all_failed_axes = set()
            for v in state["validation_results"]:
                failed_axes = [axis for axis, passed in v.pass_flags.items() if not passed]
                all_failed_axes.update(failed_axes)
            
            axis_names = {
                "read": "다단 혼입",
                "sent": "문장 단절",
                "noise": "노이즈 잔존",
                "table": "표 파싱 불가"
            }
            failure_reasons.extend([axis_names.get(axis, axis) for axis in all_failed_axes])
        
        if state["error_log"]:
            failure_reasons.append(f"에러 {len(state['error_log'])}건")
        
        # 조치 사항
        action = "Fail 확정 + Raw dump 저장"
        if state["validation_results"]:
            best_score = max(sum(v.scores.values()) for v in state["validation_results"])
            if best_score > 2.5:  # 평균 0.625
                action = "수동 검토 권장"
        
        # 새 행 추가
        row = {
            "파일 이름": state["document_name"],
            "실패 이유": ", ".join(failure_reasons) if failure_reasons else "알 수 없음",
            "조치": action
        }
        
        existing_rows.append(row)
        
        # CSV 저장
        fieldnames = ["파일 이름", "실패 이유", "조치"]
        
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)


if __name__ == "__main__":
    # 테스트
    print("[OK] ReportGenerator module loaded")

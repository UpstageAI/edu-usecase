"""
Table Enhancement 도구
표 파싱 강화
"""

from typing import Dict, List, Any
import re


class TableEnhancementTool:
    """표 파싱 강화 도구"""
    
    def __init__(self):
        self.settings = {
            "detect_grid": True,
            "normalize_units": True,
            "merge_cells": True
        }
    
    def process(self, pages: List[Dict], pdf_path: str) -> List[Dict]:
        """
        표 파싱 강화
        
        Args:
            pages: 원본 페이지 데이터
            pdf_path: PDF 파일 경로
            
        Returns:
            표가 강화된 페이지 데이터
        """
        
        processed_pages = []
        
        for page in pages:
            enhanced_page = self._enhance_tables(page)
            processed_pages.append(enhanced_page)
        
        return processed_pages
    
    def _enhance_tables(self, page: Dict) -> Dict:
        """페이지 내 표 강화"""
        
        tables = page.get("tables", [])
        
        if not tables:
            # 표가 감지되지 않은 경우, 텍스트에서 표 형식 감지 시도
            detected_tables = self._detect_tables_from_text(page)
            if detected_tables:
                tables = detected_tables
        
        # 각 표에 대해 강화
        enhanced_tables = []
        for table in tables:
            enhanced = self._enhance_single_table(table)
            enhanced_tables.append(enhanced)
        
        new_page = page.copy()
        new_page["tables"] = enhanced_tables
        new_page["source"] = page["source"] + "+table_enhancement"
        new_page["table_info"] = {
            "table_count": len(enhanced_tables),
            "enhanced": True
        }
        
        return new_page
    
    def _detect_tables_from_text(self, page: Dict) -> List[Dict]:
        """텍스트에서 표 형식 감지"""
        
        text = page.get("text", "")
        lines = text.split("\n")
        
        # 간단한 휴리스틱: 연속된 라인에서 구분자(|, \t) 패턴 찾기
        table_blocks = []
        current_table = []
        
        for line in lines:
            # 구분자가 있는 라인
            if "|" in line or "\t" in line:
                # 구분자로 분할
                if "|" in line:
                    cells = [cell.strip() for cell in line.split("|")]
                else:
                    cells = [cell.strip() for cell in line.split("\t")]
                
                # 빈 셀 제거
                cells = [c for c in cells if c]
                
                if len(cells) >= 2:  # 최소 2개 컬럼
                    current_table.append(cells)
            else:
                # 표 종료
                if len(current_table) >= 2:  # 최소 2행
                    table_blocks.append(current_table)
                current_table = []
        
        # 마지막 표
        if len(current_table) >= 2:
            table_blocks.append(current_table)
        
        # 표 딕셔너리로 변환
        detected = []
        for table_data in table_blocks:
            detected.append({
                "rows": len(table_data),
                "cols": max(len(row) for row in table_data),
                "data": table_data,
                "source": "text_detection"
            })
        
        return detected
    
    def _enhance_single_table(self, table: Dict) -> Dict:
        """단일 표 강화"""
        
        data = table.get("data", [])
        
        if not data:
            return table
        
        # 1. 단위 정규화
        if self.settings["normalize_units"]:
            data = self._normalize_units(data)
        
        # 2. 셀 병합 처리
        if self.settings["merge_cells"]:
            data = self._handle_merged_cells(data)
        
        enhanced = table.copy()
        enhanced["data"] = data
        enhanced["enhanced"] = True
        
        return enhanced
    
    def _normalize_units(self, data: List[List[str]]) -> List[List[str]]:
        """단위 정규화 (예: '1,000원' → '1000')"""
        
        normalized = []
        
        for row in data:
            normalized_row = []
            for cell in row:
                if isinstance(cell, str):
                    # 숫자 + 단위 패턴 감지
                    # 예: "1,000원", "$100", "50%" 등
                    normalized_cell = cell.replace(",", "").strip()
                else:
                    normalized_cell = cell
                
                normalized_row.append(normalized_cell)
            
            normalized.append(normalized_row)
        
        return normalized
    
    def _handle_merged_cells(self, data: List[List[str]]) -> List[List[str]]:
        """병합된 셀 처리"""
        
        # 빈 셀을 이전 셀 값으로 채우기
        handled = []
        
        for row in data:
            handled_row = []
            prev_cell = ""
            
            for cell in row:
                if isinstance(cell, str) and cell.strip() == "":
                    # 빈 셀 → 이전 값 사용
                    handled_row.append(prev_cell)
                else:
                    handled_row.append(cell)
                    prev_cell = cell
            
            handled.append(handled_row)
        
        return handled


if __name__ == "__main__":
    # 테스트
    tool = TableEnhancementTool()
    print(f"✅ TableEnhancementTool 초기화 완료")


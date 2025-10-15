"""
Layout Parser 도구
레이아웃 분석 및 읽기 순서 재정렬
"""

from typing import Dict, List, Any
import numpy as np


class LayoutParserTool:
    """레이아웃 기반 재정렬 도구"""
    
    def __init__(self):
        self.settings = {
            "column_detection": True,
            "reading_order": "top-to-bottom-left-to-right"
        }
    
    def process(self, pages: List[Dict], pdf_path: str) -> List[Dict]:
        """
        레이아웃 기반 재정렬
        
        Args:
            pages: 원본 페이지 데이터
            pdf_path: PDF 파일 경로
            
        Returns:
            재정렬된 페이지 데이터
        """
        
        processed_pages = []
        
        for page in pages:
            # bbox 정보가 있으면 재정렬
            if page.get("bbox"):
                reordered_page = self._reorder_page(page)
                processed_pages.append(reordered_page)
            else:
                processed_pages.append(page)
        
        return processed_pages
    
    def _reorder_page(self, page: Dict) -> Dict:
        """페이지 내 텍스트 블록 재정렬"""
        
        bbox_list = page["bbox"]
        
        if not bbox_list:
            return page
        
        # 다단 감지
        columns = self._detect_columns(bbox_list, page.get("width", 800))
        
        # 각 컬럼별로 정렬
        sorted_bbox = []
        for col_bbox_list in columns:
            # Y 좌표 기준으로 정렬 (위에서 아래로)
            col_sorted = sorted(col_bbox_list, key=lambda b: b["y0"])
            sorted_bbox.extend(col_sorted)
        
        # 재정렬된 텍스트 재구성
        reordered_text = " ".join([b["text"] for b in sorted_bbox])
        
        new_page = page.copy()
        new_page["text"] = reordered_text
        new_page["bbox"] = sorted_bbox
        new_page["source"] = page["source"] + "+layout"
        new_page["layout_info"] = {
            "columns_detected": len(columns),
            "reordered": True
        }
        
        return new_page
    
    def _detect_columns(self, bbox_list: List[Dict], page_width: float) -> List[List[Dict]]:
        """다단 레이아웃 감지"""
        
        # X 좌표 중심점 추출
        x_centers = [(bbox["x0"] + bbox["x1"]) / 2 for bbox in bbox_list]
        
        if not x_centers:
            return [bbox_list]
        
        # 간단한 K-means 스타일 클러스터링
        # 일단 2단 가정
        threshold = page_width / 2
        
        left_column = []
        right_column = []
        
        for bbox in bbox_list:
            x_center = (bbox["x0"] + bbox["x1"]) / 2
            
            if x_center < threshold:
                left_column.append(bbox)
            else:
                right_column.append(bbox)
        
        # 왼쪽 컬럼 먼저, 오른쪽 컬럼 나중
        columns = []
        if left_column:
            columns.append(left_column)
        if right_column:
            columns.append(right_column)
        
        return columns if len(columns) > 1 else [bbox_list]


if __name__ == "__main__":
    # 테스트
    tool = LayoutParserTool()
    print(f"✅ LayoutParserTool 초기화 완료")


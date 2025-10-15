"""
PDFMiner.six 도구
텍스트 레이어 추출 (레이아웃 분석 강화)
"""

from pdfminer.high_level import extract_pages, extract_text
from pdfminer.layout import LTTextContainer, LTChar, LTTextBox, LTTextLine
from typing import Dict, List, Any, Union
from pathlib import Path


class PDFMinerTool:
    """PDFMiner.six를 이용한 텍스트 추출"""
    
    def __init__(self):
        self.settings = {
            "line_margin": 0.5,
            "word_margin": 0.1,
            "char_margin": 2.0
        }
    
    def extract(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """
        PDF 파일에서 텍스트 추출
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            {
                "pages": [{"page": 1, "source": "pdfminer", "text": "...", "bbox": [...]}],
                "settings": {...}
            }
        """
        
        # Path 객체로 변환
        if not isinstance(pdf_path, Path):
            pdf_path = Path(pdf_path)
        
        pages_data = []
        
        try:
            # 페이지별 추출
            for page_num, page_layout in enumerate(extract_pages(str(pdf_path)), 1):
                # 텍스트 추출
                text_elements = []
                bbox_elements = []
                
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        text_elements.append(element.get_text())
                        
                        # bbox 정보 추출
                        try:
                            bbox_elements.append({
                                "text": element.get_text().strip(),
                                "x0": float(element.x0),
                                "y0": float(element.y0),
                                "x1": float(element.x1),
                                "y1": float(element.y1),
                                "top": float(element.y0),
                                "bottom": float(element.y1)
                            })
                        except:
                            pass
                
                page_text = "".join(text_elements)
                
                page_data = {
                    "page": page_num,
                    "source": "pdfminer",
                    "text": page_text,
                    "bbox": bbox_elements,
                    "tables": [],  # PDFMiner는 기본적으로 표 감지 안 함
                    "width": float(page_layout.width),
                    "height": float(page_layout.height)
                }
                
                pages_data.append(page_data)
        
        except Exception as e:
            print(f"[ERROR] PDFMiner extraction failed: {e}")
            return {"pages": [], "settings": self.settings}
        
        return {
            "pages": pages_data,
            "settings": self.settings
        }
    
    def process(self, pages: List[Dict], pdf_path: Union[str, Path]) -> List[Dict]:
        """
        폴백 도구 인터페이스 (2단계 호환)
        
        Args:
            pages: 페이지 데이터 리스트
            pdf_path: PDF 파일 경로
            
        Returns:
            처리된 페이지 데이터
        """
        # 기본 extract와 동일
        result = self.extract(pdf_path)
        return result["pages"]


if __name__ == "__main__":
    # 테스트
    tool = PDFMinerTool()
    print("[OK] PDFMinerTool initialized")


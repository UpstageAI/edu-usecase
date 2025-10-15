"""
pdfplumber 도구
텍스트 레이어 추출
"""

import pdfplumber
from typing import Dict, List, Any, Union
from pathlib import Path
from .. import config


class PDFPlumberTool:
    """pdfplumber를 이용한 텍스트 추출"""
    
    def __init__(self):
        self.settings = {
            "layout_width_tolerance": config.PDF_PLUMBER_LAYOUT_WIDTH_TOLERANCE,
            "layout_height_tolerance": config.PDF_PLUMBER_LAYOUT_HEIGHT_TOLERANCE
        }
    
    def extract(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """
        PDF 파일에서 텍스트 추출
        
        Args:
            pdf_path: PDF 파일 경로 (str 또는 Path 객체)
            
        Returns:
            {
                "pages": [{"page": 1, "source": "plumber", "text": "...", "bbox": [...]}],
                "settings": {...}
            }
        """
        
        # Path 객체로 변환 (한글 경로 처리)
        if not isinstance(pdf_path, Path):
            pdf_path = Path(pdf_path)
        
        pages_data = []
        
        # Windows에서 한글 경로 처리를 위해 파일을 바이너리로 읽어서 전달
        with open(pdf_path, 'rb') as f:
            with pdfplumber.open(f) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 텍스트 추출
                    text = page.extract_text() or ""
                    
                    # 단어별 bbox 정보 (안전하게 처리)
                    words = page.extract_words() or []
                    
                    # 테이블 감지
                    tables = page.extract_tables() or []
                    
                    page_data = {
                        "page": page_num,
                        "source": "plumber",
                        "text": text,
                        "bbox": [
                            {
                                "text": word.get("text", ""),
                                "x0": word.get("x0", 0),
                                "y0": word.get("y0", 0),
                                "x1": word.get("x1", 0),
                                "y1": word.get("y1", 0),
                                "top": word.get("top", 0),
                                "bottom": word.get("bottom", 0)
                            }
                            for word in words
                            if word and isinstance(word, dict)
                        ],
                        "tables": [
                            {
                                "rows": len(table),
                                "cols": len(table[0]) if table else 0,
                                "data": table
                            }
                            for table in tables
                        ] if tables else [],
                        "width": page.width,
                        "height": page.height
                    }
                    
                    pages_data.append(page_data)
        
        return {
            "pages": pages_data,
            "settings": self.settings
        }
    
    def get_version(self) -> str:
        """pdfplumber 버전 반환"""
        return pdfplumber.__version__


if __name__ == "__main__":
    # 테스트
    tool = PDFPlumberTool()
    print(f"✅ PDFPlumberTool 초기화 완료 (version: {tool.get_version()})")


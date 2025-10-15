"""
PyPDFium2 도구
Chromium 기반 고속 PDF 렌더링 + 텍스트 추출
"""

try:
    import pypdfium2 as pdfium
    PYPDFIUM2_AVAILABLE = True
except ImportError:
    PYPDFIUM2_AVAILABLE = False
    print("[WARNING] pypdfium2 not installed. Install with: pip install pypdfium2")

from typing import Dict, List, Any, Union
from pathlib import Path


class PyPDFium2Tool:
    """PyPDFium2를 이용한 텍스트 추출"""
    
    def __init__(self):
        self.settings = {
            "text_mode": "layout"  # layout or raw
        }
        
        if not PYPDFIUM2_AVAILABLE:
            print("[WARNING] PyPDFium2Tool initialized but library not available")
    
    def extract(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """
        PDF 파일에서 텍스트 추출
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            {
                "pages": [{"page": 1, "source": "pypdfium2", "text": "...", "bbox": [...]}],
                "settings": {...}
            }
        """
        
        if not PYPDFIUM2_AVAILABLE:
            return {"pages": [], "settings": self.settings}
        
        # Path 객체로 변환
        if not isinstance(pdf_path, Path):
            pdf_path = Path(pdf_path)
        
        pages_data = []
        
        try:
            # PDF 열기
            pdf = pdfium.PdfDocument(str(pdf_path))
            
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                
                # 텍스트 추출
                textpage = page.get_textpage()
                text = textpage.get_text_range()
                
                # 페이지 크기
                width, height = page.get_size()
                
                # bbox 정보 (간단히 처리)
                bbox_elements = []
                
                # PyPDFium2는 텍스트를 문자 단위로 추출 가능
                # 여기서는 간단히 전체 텍스트만 사용
                if text.strip():
                    bbox_elements.append({
                        "text": text.strip(),
                        "x0": 0,
                        "y0": 0,
                        "x1": width,
                        "y1": height,
                        "top": 0,
                        "bottom": height
                    })
                
                page_data = {
                    "page": page_num + 1,
                    "source": "pypdfium2",
                    "text": text,
                    "bbox": bbox_elements,
                    "tables": [],  # PyPDFium2는 표 감지 안 함
                    "width": float(width),
                    "height": float(height)
                }
                
                pages_data.append(page_data)
                
                # 리소스 해제
                textpage.close()
                page.close()
            
            pdf.close()
        
        except Exception as e:
            print(f"[ERROR] PyPDFium2 extraction failed: {e}")
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
    tool = PyPDFium2Tool()
    if PYPDFIUM2_AVAILABLE:
        print("[OK] PyPDFium2Tool initialized")
    else:
        print("[WARNING] PyPDFium2Tool initialized but library not available")


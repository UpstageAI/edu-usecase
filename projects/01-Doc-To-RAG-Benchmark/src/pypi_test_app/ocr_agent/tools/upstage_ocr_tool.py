"""
Upstage OCR Tool
Upstage OCR API를 사용한 텍스트 추출
"""

import requests
import os
from pathlib import Path
from typing import Dict, List, Any, Union


class UpstageOCRTool:
    """
    Upstage OCR API 기반 텍스트 추출
    
    특징:
    - 이미지 기반 PDF도 처리 가능
    - OCR 기반 텍스트 추출
    - 표, 좌표 정보 제공
    """
    
    def __init__(self):
        self.api_key = os.getenv("SOLAR_API_KEY")
        if not self.api_key:
            raise ValueError("SOLAR_API_KEY not found in environment variables")
        
        self.api_url = "https://api.upstage.ai/v1/document-ai/ocr"
    
    def get_version(self) -> str:
        """도구 버전 반환"""
        return "upstage-ocr-v1"
    
    def extract(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Upstage OCR API로 PDF 추출
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            {
                "pages": [
                    {
                        "page": 1,
                        "text": "추출된 텍스트",
                        "bbox": [...],
                        "tables": [...]
                    }
                ],
                "settings": {...}
            }
        """
        
        if not isinstance(pdf_path, Path):
            pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # PDF 파일을 바이너리로 읽기
            with open(pdf_path, 'rb') as f:
                files = {"document": f}
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                # API 호출
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    timeout=120  # OCR은 시간이 걸릴 수 있음
                )
                
                response.raise_for_status()
                result = response.json()
            
            # 응답 파싱
            pages = self._parse_upstage_response(result)
            
            return {
                "pages": pages,
                "settings": {
                    "api": "upstage-ocr",
                    "version": self.get_version()
                }
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Upstage OCR API error: {e}")
            raise
        except Exception as e:
            print(f"[ERROR] Upstage OCR processing error: {e}")
            raise
    
    def _parse_upstage_response(self, response: Dict) -> List[Dict]:
        """
        Upstage OCR API 응답을 표준 형식으로 변환
        
        Args:
            response: Upstage API 응답
            
        Returns:
            페이지 리스트
        """
        pages = []
        
        # Upstage OCR 응답 구조에 따라 파싱
        # 실제 API 응답 구조에 맞게 수정 필요
        if "pages" in response:
            for idx, page_data in enumerate(response["pages"], 1):
                # 텍스트 추출
                text = page_data.get("text", "")
                
                # 바운딩 박스 정보
                bbox = []
                if "coordinates" in page_data:
                    for coord in page_data["coordinates"]:
                        bbox.append({
                            "x0": coord.get("x", 0),
                            "y0": coord.get("y", 0),
                            "x1": coord.get("x", 0) + coord.get("width", 0),
                            "y1": coord.get("y", 0) + coord.get("height", 0),
                            "text": coord.get("text", "")
                        })
                
                # 표 정보
                tables = []
                if "tables" in page_data:
                    for table_data in page_data["tables"]:
                        tables.append({
                            "rows": table_data.get("rows", 0),
                            "cols": table_data.get("cols", 0),
                            "data": table_data.get("data", [])
                        })
                
                pages.append({
                    "page": idx,
                    "text": text,
                    "bbox": bbox,
                    "tables": tables,
                    "width": page_data.get("width", 0),
                    "height": page_data.get("height", 0)
                })
        
        # 만약 다른 구조라면 (content 필드에 전체 텍스트가 있는 경우)
        elif "content" in response:
            pages.append({
                "page": 1,
                "text": response["content"],
                "bbox": [],
                "tables": [],
                "width": 0,
                "height": 0
            })
        
        return pages
    
    def process(self, pages: List[Dict], document_path: str) -> List[Dict]:
        """
        폴백 처리용 메서드 (OCR 재실행은 비효율적이므로 원본 반환)
        
        Args:
            pages: 페이지 데이터 리스트
            document_path: 문서 경로
            
        Returns:
            처리된 페이지 리스트 (원본 그대로)
        """
        # OCR을 폴백으로 재실행하는 것은 비효율적이므로
        # 이미 추출된 결과를 그대로 반환
        return pages


if __name__ == "__main__":
    # 테스트
    import sys
    
    if len(sys.argv) > 1:
        test_pdf = sys.argv[1]
    else:
        test_pdf = "../fin_pdf_files/카카오뱅크_20240508_한화투자증권.pdf"
    
    if Path(test_pdf).exists():
        try:
            tool = UpstageOCRTool()
            result = tool.extract(test_pdf)
            
            print(f"[OK] Upstage OCR extraction completed")
            print(f"Pages: {len(result['pages'])}")
            
            if result['pages']:
                first_page = result['pages'][0]
                print(f"\nFirst page preview:")
                print(f"  Text length: {len(first_page['text'])} chars")
                print(f"  Text sample: {first_page['text'][:200]}...")
                print(f"  Bbox count: {len(first_page['bbox'])}")
                print(f"  Tables: {len(first_page['tables'])}")
        except Exception as e:
            print(f"[ERROR] Test failed: {e}")
    else:
        print(f"[ERROR] Test file not found: {test_pdf}")


"""
Upstage Document Parse Tool
Upstage Document Parsing API를 사용한 문서 파싱
"""

import requests
import os
from pathlib import Path
from typing import Dict, List, Any, Union


class UpstageDocumentParseTool:
    """
    Upstage Document Parsing API 기반 문서 파싱
    
    특징:
    - 문서 구조 인식 (제목, 문단, 표 등)
    - 레이아웃 분석
    - 고급 파싱 기능
    """
    
    def __init__(self):
        self.api_key = os.getenv("SOLAR_API_KEY")
        if not self.api_key:
            raise ValueError("SOLAR_API_KEY not found in environment variables")
        
        self.api_url = "https://api.upstage.ai/v1/document-ai/document-parse"
    
    def get_version(self) -> str:
        """도구 버전 반환"""
        return "upstage-document-parse-v1"
    
    def extract(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Upstage Document Parse API로 PDF 추출
        
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
                
                # API 파라미터
                data = {
                    "ocr": "auto",  # OCR 자동 감지
                    "output_formats": ["text", "html"],
                }
                
                # API 호출
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=120  # 문서 파싱은 시간이 걸릴 수 있음
                )
                
                response.raise_for_status()
                result = response.json()
            
            # 응답 파싱
            pages = self._parse_upstage_response(result)
            
            return {
                "pages": pages,
                "settings": {
                    "api": "upstage-document-parse",
                    "version": self.get_version(),
                    "ocr": "auto"
                }
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Upstage Document Parse API error: {e}")
            raise
        except Exception as e:
            print(f"[ERROR] Upstage Document Parse processing error: {e}")
            raise
    
    def _parse_upstage_response(self, response: Dict) -> List[Dict]:
        """
        Upstage Document Parse API 응답을 표준 형식으로 변환
        
        Args:
            response: Upstage API 응답
            
        Returns:
            페이지 리스트
        """
        pages = []
        
        # Upstage Document Parse 응답 구조에 따라 파싱
        # 실제 API 응답 구조에 맞게 수정 필요
        if "elements" in response:
            # 엘리먼트 기반 파싱
            page_texts = {}
            page_bboxes = {}
            page_tables = {}
            
            for element in response["elements"]:
                page_num = element.get("page", 1)
                
                if page_num not in page_texts:
                    page_texts[page_num] = []
                    page_bboxes[page_num] = []
                    page_tables[page_num] = []
                
                # 텍스트 추출
                if element.get("type") in ["text", "paragraph", "heading"]:
                    page_texts[page_num].append(element.get("content", ""))
                    
                    # 바운딩 박스
                    if "coordinates" in element:
                        coord = element["coordinates"]
                        page_bboxes[page_num].append({
                            "x0": coord.get("x", 0),
                            "y0": coord.get("y", 0),
                            "x1": coord.get("x", 0) + coord.get("width", 0),
                            "y1": coord.get("y", 0) + coord.get("height", 0),
                            "text": element.get("content", "")
                        })
                
                # 표 추출
                elif element.get("type") == "table":
                    table_data = element.get("table", {})
                    page_tables[page_num].append({
                        "rows": len(table_data.get("rows", [])),
                        "cols": len(table_data.get("rows", [[]])[0]) if table_data.get("rows") else 0,
                        "data": table_data.get("rows", [])
                    })
            
            # 페이지별로 정리
            for page_num in sorted(page_texts.keys()):
                pages.append({
                    "page": page_num,
                    "text": "\n".join(page_texts[page_num]),
                    "bbox": page_bboxes[page_num],
                    "tables": page_tables[page_num],
                    "width": 0,
                    "height": 0
                })
        
        # 단순 텍스트 응답인 경우
        elif "content" in response:
            pages.append({
                "page": 1,
                "text": response["content"].get("text", ""),
                "bbox": [],
                "tables": [],
                "width": 0,
                "height": 0
            })
        
        # HTML 파싱
        elif "html" in response:
            # HTML을 텍스트로 변환 (간단한 처리)
            import re
            html_text = response["html"]
            # HTML 태그 제거
            text = re.sub(r'<[^>]+>', ' ', html_text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            pages.append({
                "page": 1,
                "text": text,
                "bbox": [],
                "tables": [],
                "width": 0,
                "height": 0
            })
        
        return pages if pages else [{"page": 1, "text": "", "bbox": [], "tables": [], "width": 0, "height": 0}]
    
    def process(self, pages: List[Dict], document_path: str) -> List[Dict]:
        """
        폴백 처리용 메서드 (문서 파싱 재실행은 비효율적이므로 원본 반환)
        
        Args:
            pages: 페이지 데이터 리스트
            document_path: 문서 경로
            
        Returns:
            처리된 페이지 리스트 (원본 그대로)
        """
        # 문서 파싱을 폴백으로 재실행하는 것은 비효율적이므로
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
            tool = UpstageDocumentParseTool()
            result = tool.extract(test_pdf)
            
            print(f"[OK] Upstage Document Parse extraction completed")
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


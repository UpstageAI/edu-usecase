"""
기본 추출 Agent (1단계)
다중 라이브러리로 원본 텍스트 추출
"""

import time
import json
import random
from pathlib import Path
from typing import List, Union, Any, Optional
from datetime import datetime

from ..state import DocumentState, ExtractionResult, PageExtractionResult, add_extraction_result
from .. import config
from ..tools.pdfplumber_tool import PDFPlumberTool
from ..tools.pdfminer_tool import PDFMinerTool
from ..tools.pypdfium2_tool import PyPDFium2Tool
from ..tools.upstage_ocr_tool import UpstageOCRTool
from ..tools.upstage_document_parse_tool import UpstageDocumentParseTool


class BasicExtractionAgent:
    """
    1단계: 기본 추출 에이전트
    
    역할:
    - 5개 도구로 다중 추출:
      1. PDFPlumber (로컬)
      2. PDFMiner (로컬)
      3. PyPDFium2 (로컬)
      4. Upstage OCR API
      5. Upstage Document Parse API
    - 페이지 샘플링 (최대 5페이지)
    - 최소 가공 원칙 (정렬/교정/헤더 제거 X)
    - 원본 좌표 그대로 저장
    - 각 도구별 조합 생성 → 2단계에서 검증
    """
    
    def __init__(self):
        self.tools = {
            "pdfplumber": PDFPlumberTool(),
            "pdfminer": PDFMinerTool(),
            "pypdfium2": PyPDFium2Tool(),
            "upstage_ocr": UpstageOCRTool(),
            "upstage_document_parse": UpstageDocumentParseTool()
        }
    
    def run(self, state: DocumentState) -> DocumentState:
        """기본 추출 실행 (다중 라이브러리)"""
        
        document_path = state["document_path"]
        document_name = state["document_name"]
        
        print(f"\n{'='*60}")
        print(f"[EXTRACTION] Document: {document_name}")
        print(f"{'='*60}\n")
        
        # 모든 라이브러리로 추출
        for idx, (tool_name, tool) in enumerate(self.tools.items(), 1):
            print(f"[{idx}/{len(self.tools)}] {tool_name} extraction starting...")
            
            result = self._extract_with_tool(
                tool_name, 
                tool, 
                document_path, 
                document_name
            )
            
            if result:
                state = add_extraction_result(state, result)
                print(f"[OK] {tool_name} completed: {result.page_count} pages, {result.processing_time_ms:.0f}ms")
            else:
                print(f"[WARN] {tool_name} failed")
        
        # 문서 메타데이터 저장
        state["doc_meta"] = {
            "document_name": document_name,
            "document_path": document_path,
            "extraction_count": len(state["extraction_results"]),
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n[SUMMARY] Extraction completed: {len(state['extraction_results'])} libraries")
        for result in state["extraction_results"]:
            print(f"  - {result.strategy}: {result.page_count} pages")
        print()
        
        return state
    
    def _sample_pages(self, total_pages: int, max_samples: int = 5) -> List[int]:
        """페이지 샘플링 (랜덤, 최대 5개)"""
        if total_pages <= max_samples:
            # 전체 페이지가 5개 이하면 모두 사용
            return list(range(1, total_pages + 1))
        else:
            # 랜덤하게 5페이지 선택
            return sorted(random.sample(range(1, total_pages + 1), max_samples))
    
    def _calculate_extraction_cost(self, tool_name: str, page_count: int) -> float:
        """
        추출 비용 계산 (API 사용 시)
        
        Args:
            tool_name: 도구 이름
            page_count: 처리한 페이지 수
            
        Returns:
            비용 (USD)
        """
        cost_per_page = config.UPSTAGE_API_PRICING.get(tool_name, 0.0)
        return cost_per_page * page_count
    
    def _extract_with_tool(
        self, 
        tool_name: str,
        tool: Any, 
        document_path: Union[str, Path], 
        document_name: str
    ) -> ExtractionResult:
        """범용 도구로 텍스트 추출 (페이지 샘플링)"""
        
        # Path 객체로 변환 (한글 경로 처리)
        if not isinstance(document_path, Path):
            document_path = Path(document_path)
        
        start_time = time.time()
        
        try:
            # 전체 추출 실행 (페이지 수 확인용)
            result = tool.extract(document_path)
            total_pages = len(result["pages"])
            
            # 페이지 샘플링
            sampled_pages = self._sample_pages(total_pages, max_samples=5)
            print(f"[SAMPLING] Selected {len(sampled_pages)} pages from {total_pages} total: {sampled_pages}")
            
            # 전체 처리 시간 측정
            processing_time = (time.time() - start_time) * 1000  # ms
            
            # API 비용 계산
            api_cost = self._calculate_extraction_cost(tool_name, len(sampled_pages))
            
            # 샘플링된 페이지만 추출 (페이지당 평균 시간 계산)
            page_results = []
            avg_time_per_page = processing_time / len(sampled_pages) if sampled_pages else 0.0
            
            for page_data in result["pages"]:
                page_num = page_data["page"]
                if page_num in sampled_pages:
                    page_result = PageExtractionResult(
                        page_num=page_num,
                        strategy=tool_name,
                        text=page_data["text"],
                        bbox=page_data.get("bbox", []),
                        tables=page_data.get("tables", []),
                        processing_time_ms=avg_time_per_page,
                        status="success",
                        metadata={
                            "width": page_data.get("width", 0),
                            "height": page_data.get("height", 0)
                        }
                    )
                    page_results.append(page_result)
            
            # 결과 저장
            output_dir = config.EXTRACTED_DIR / document_name.replace('.pdf', '') / tool_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            pages_text_path = output_dir / "pages_text_sampled.jsonl"
            doc_meta_path = output_dir / "doc_meta.json"
            
            # pages_text_sampled.jsonl 저장 (샘플링된 페이지만)
            with open(pages_text_path, 'w', encoding='utf-8') as f:
                for page_result in page_results:
                    page_dict = {
                        "page": page_result.page_num,
                        "source": page_result.strategy,
                        "text": page_result.text,
                        "bbox": page_result.bbox,
                        "tables": page_result.tables
                    }
                    f.write(json.dumps(page_dict, ensure_ascii=False) + '\n')
            
            # doc_meta.json 저장
            meta = {
                "engine": tool_name,
                "version": getattr(tool, 'get_version', lambda: "unknown")(),
                "settings": result["settings"],
                "total_page_count": total_pages,
                "sampled_page_count": len(sampled_pages),
                "sampled_pages": sampled_pages,
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            with open(doc_meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            
            return ExtractionResult(
                strategy=tool_name,
                pages_text_path=str(pages_text_path),
                doc_meta_path=str(doc_meta_path),
                sampled_pages=sampled_pages,
                page_results=page_results,
                processing_time_ms=processing_time,
                extraction_cost_usd=api_cost,
                page_count=len(sampled_pages),
                total_page_count=total_pages,
                status="success",
                metadata=meta
            )
            
        except Exception as e:
            print(f"[ERROR] {tool_name} 에러: {str(e)}")
            return ExtractionResult(
                strategy=tool_name,
                pages_text_path="",
                doc_meta_path="",
                status="failed",
                error_message=str(e)
            )


if __name__ == "__main__":
    # 테스트
    from ..state import create_initial_document_state
    
    test_pdf = "../fin_pdf_files/카카오뱅크_20240508_한화투자증권.pdf"
    
    if Path(test_pdf).exists():
        state = create_initial_document_state(test_pdf)
        agent = BasicExtractionAgent()
        state = agent.run(state)
        
        print("\n" + "="*60)
        print("[OK] Test completed")
        print(f"추출 결과 수: {len(state['extraction_results'])}")
        for result in state["extraction_results"]:
            print(f"  - {result.strategy}: {result.status}, {result.page_count}페이지")
    else:
        print(f"[ERROR] Test file not found: {test_pdf}")


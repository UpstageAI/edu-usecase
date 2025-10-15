"""
유효성 검증을 위한 Solar LLM 프롬프트
2단계에서 텍스트 추출 결과가 유효한지 Pass/Fail 판단
"""

import json
from typing import Dict, List, Any


def create_validation_prompt(
    page_text: str,
    page_num: int,
    strategy: str,
    has_tables: bool = False,
    table_preview: str = ""
) -> str:
    """
    유효성 검증 프롬프트 생성
    
    Args:
        page_text: 추출된 텍스트
        page_num: 페이지 번호
        strategy: 추출 전략 (예: 'pdfplumber', 'pdfplumber+custom_split')
        has_tables: 표 포함 여부
        table_preview: 표 미리보기 (있는 경우)
        
    Returns:
        Solar LLM용 프롬프트
    """
    
    prompt = f"""당신은 PDF 텍스트 추출 결과를 검증하는 전문가입니다.

📄 **문서 정보**
- 페이지: {page_num}
- 추출 전략: {strategy}
- 표 포함: {'예' if has_tables else '아니오'}

📝 **추출된 텍스트:**
```
{page_text[:2000]}  # 처음 2000자만
{f"... (총 {len(page_text)}자)" if len(page_text) > 2000 else ""}
```
"""

    if has_tables and table_preview:
        prompt += f"""

📊 **표 미리보기:**
```
{table_preview[:500]}
```
"""

    prompt += """

🎯 **검증 기준:**

다음 항목들을 **종합적으로 판단**하여 이 텍스트 추출 결과가 **실제로 사용 가능한지** 평가해주세요:

1. **문장의 자연스러움**
   - 문장이 의미상 자연스럽고 이해 가능한가?
   - 단어들이 올바른 순서로 배열되어 있는가?
   - 문장이 중간에 끊기거나 뒤섞이지 않았는가?

2. **읽기 순서**
   - 문단과 문장의 흐름이 논리적인가?
   - 다단(multi-column) 레이아웃이 올바르게 처리되었는가?
   - 좌→우, 위→아래 순서가 자연스러운가?

3. **노이즈 제거**
   - 불필요한 헤더/푸터가 제거되었는가?
   - 페이지 번호가 본문에 섞여있지 않은가?
   - 반복되는 노이즈 패턴이 없는가?

4. **표 및 구조적 요소** (표가 있는 경우)
   - 표의 행과 열이 올바르게 구분되었는가?
   - 셀의 내용이 정렬되어 있는가?
   - 표 구조가 유지되었는가?

5. **전체적인 가독성**
   - 이 텍스트를 사람이 읽고 이해할 수 있는가?
   - 핵심 정보가 손실되지 않았는가?
   - 추출 결과가 실무에서 사용 가능한 수준인가?

📤 **응답 형식:**

JSON 형식으로 응답해주세요:

```json
{
  "pass": true,  // 또는 false
  "confidence": 0.95,  // 0.0~1.0, 판단의 확신도
  "reason": "전반적으로 우수한 추출 결과입니다. 문장이 자연스럽고 읽기 순서가 올바르며 노이즈가 없습니다.",
  "issues": [],  // pass인 경우 빈 배열, fail인 경우 ["문장 단절", "다단 혼입"] 등
  "suggestions": []  // fail인 경우 개선 방법 제안 ["custom_split 사용", "layout_reorder 필요"]
}
```

**판단 원칙:**
- **PASS**: 실무에서 사용 가능한 수준 (완벽하지 않아도 괜찮음, 핵심 정보 전달 가능)
- **FAIL**: 심각한 문제가 있어서 실무 사용 불가 (문장 뒤섞임, 심각한 단절, 표 구조 깨짐 등)
- 사소한 오타나 미세한 노이즈는 PASS로 처리 (너무 엄격하게 판단하지 말 것)
- 전체적인 가독성과 정보 전달 여부를 최우선으로 고려

JSON만 출력하세요 (다른 설명 없이):"""

    return prompt


def parse_validation_response(response_text: str) -> Dict[str, Any]:
    """
    Solar LLM 응답 파싱
    
    Args:
        response_text: LLM 응답 텍스트
        
    Returns:
        {
            'pass': bool,
            'confidence': float,
            'reason': str,
            'issues': List[str],
            'suggestions': List[str]
        }
    """
    
    try:
        # JSON 블록 추출
        text = response_text.strip()
        
        # ```json ... ``` 형식 처리
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        # JSON 파싱
        result = json.loads(text)
        
        # 필수 필드 검증
        return {
            'pass': result.get('pass', False),
            'confidence': float(result.get('confidence', 0.5)),
            'reason': result.get('reason', ''),
            'issues': result.get('issues', []),
            'suggestions': result.get('suggestions', [])
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to parse validation response: {e}")
        print(f"Response text: {response_text[:200]}")
        
        # 기본값 반환 (안전하게 Fail로)
        return {
            'pass': False,
            'confidence': 0.0,
            'reason': f'Failed to parse LLM response: {str(e)}',
            'issues': ['parse_error'],
            'suggestions': []
        }


def create_validation_prompt_batch(
    pages_data: List[Dict[str, Any]],
    strategy: str
) -> List[str]:
    """
    여러 페이지에 대한 프롬프트 일괄 생성
    
    Args:
        pages_data: 페이지 데이터 리스트
        strategy: 추출 전략
        
    Returns:
        프롬프트 리스트
    """
    
    prompts = []
    
    for page in pages_data:
        page_num = page.get('page', 0)
        text = page.get('text', '')
        tables = page.get('tables', [])
        
        has_tables = len(tables) > 0
        table_preview = ""
        
        if has_tables and tables:
            # 첫 번째 표 미리보기
            first_table = tables[0]
            table_preview = f"행: {first_table.get('rows', 0)}, 열: {first_table.get('cols', 0)}"
            if 'data' in first_table and first_table['data']:
                table_preview += f"\n데이터: {str(first_table['data'][:3])}"
        
        prompt = create_validation_prompt(
            page_text=text,
            page_num=page_num,
            strategy=strategy,
            has_tables=has_tables,
            table_preview=table_preview
        )
        
        prompts.append(prompt)
    
    return prompts


if __name__ == "__main__":
    # 테스트
    test_text = """
    제1장 서론
    
    본 보고서는 2024년 상반기 실적을 분석한 문서입니다.
    매출은 전년 대비 15% 증가하였으며, 영업이익은 안정적으로 유지되었습니다.
    
    다음 장에서는 세부 사항을 다룹니다.
    """
    
    prompt = create_validation_prompt(
        page_text=test_text,
        page_num=1,
        strategy="pdfplumber",
        has_tables=False
    )
    
    print("[OK] Validation prompt generated")
    print(f"Prompt length: {len(prompt)} chars")
    print("\n" + "="*60)
    print(prompt[:500] + "...")

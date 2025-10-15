"""
평가 지표 계산 (페이지별 Yes/No 체크)
유효성 검증을 위한 단순하고 명확한 메트릭
"""

import re
from typing import Dict, List, Any, Tuple
from collections import Counter


class ValidationMetrics:
    """유효성 검증 메트릭 - 페이지별 Pass/Fail 판정"""
    
    def __init__(self):
        pass
    
    def evaluate_reading_order(self, pages: List[Dict]) -> float:
        """
        read: 읽기 순서 평가 (다단 혼입 감지)
        
        기준:
        - PASS (1.0): Y좌표 역전이 5% 미만
        - FAIL (0.0): Y좌표 역전이 5% 이상
        
        Returns:
            1.0 (Pass) or 0.0 (Fail)
        """
        
        if not pages:
            return 0.0
        
        for page in pages:
            bbox_list = page.get("bbox", [])
            
            if len(bbox_list) < 2:
                # bbox가 너무 적으면 판단 불가 → Pass로 간주
                continue
            
            # Y 좌표 기준 역전 횟수 카운트
            reversals = 0
            prev_y = 0
            
            for bbox in bbox_list:
                y = bbox.get("y0", 0)
                
                # 이전 요소보다 위에 있으면 역전 (10px 오차 허용)
                if prev_y > 0 and y < prev_y - 10:
                    reversals += 1
                
                prev_y = y
            
            # 역전 비율 계산
            reversal_ratio = reversals / len(bbox_list)
            
            # 5% 이상 역전 → FAIL
            if reversal_ratio >= 0.05:
                return 0.0
        
        return 1.0
    
    def evaluate_sentence_integrity(self, pages: List[Dict]) -> float:
        """
        sent: 문장 완결성 평가 (문장 단절 감지)
        
        기준:
        - PASS (1.0):
          * 텍스트 길이 ≥ 50자
          * 평균 문장 길이 10~300자
          * 종결 어미 비율 ≥ 30%
        
        - FAIL (0.0):
          * 텍스트 길이 < 50자
          * 평균 문장 길이 < 10자 (과도한 단절)
          * 평균 문장 길이 > 500자 (병합 의심)
          * 종결 어미 비율 < 30%
        
        Returns:
            1.0 (Pass) or 0.0 (Fail)
        """
        
        full_text = " ".join([page.get("text", "") for page in pages])
        full_text = full_text.strip()
        
        # 1. 텍스트가 너무 짧으면 FAIL
        if len(full_text) < 50:
            return 0.0
        
        # 2. 문장 분할
        # 한국어: 마침표, 물음표, 느낌표 + 종결어미
        sentences = re.split(r'[.!?]+\s+|\n+', full_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) == 0:
            return 0.0
        
        # 3. 평균 문장 길이 체크
        avg_length = sum(len(s) for s in sentences) / len(sentences)
        
        if avg_length < 10:  # 너무 짧음 (단절)
            return 0.0
        
        if avg_length > 500:  # 너무 김 (병합)
            return 0.0
        
        # 4. 종결 어미 비율 체크
        sentence_endings = ['다', '요', '니다', '습니다', '음', '까', '네', '자', '.', '?', '!']
        ending_count = sum(
            1 for s in sentences 
            if any(s.endswith(e) for e in sentence_endings)
        )
        ending_ratio = ending_count / len(sentences)
        
        # 종결 어미 비율이 30% 미만이면 FAIL
        if ending_ratio < 0.30:
            return 0.0
        
        return 1.0
    
    def evaluate_noise_removal(self, pages: List[Dict]) -> float:
        """
        noise: 노이즈 제거 평가 (페이지별 단독 검사)
        
        기준:
        - PASS (1.0): 노이즈 패턴 없음
        
        - FAIL (0.0):
          * 페이지 번호 패턴 발견 (예: "1", "페이지 5", "3/10")
          * 동일 단어 5회 이상 연속 반복
          * 특수문자 비율 > 30%
          * 숫자만으로 구성된 라인이 30% 이상
        
        Returns:
            1.0 (Pass) or 0.0 (Fail)
        """
        
        for page in pages:
            text = page.get("text", "")
            
            if not text.strip():
                continue
            
            lines = text.split("\n")
            lines = [l.strip() for l in lines if l.strip()]
            
            if len(lines) == 0:
                continue
            
            # 1. 페이지 번호 패턴 감지
            page_number_pattern = re.compile(
                r'^\d{1,3}$|^페이지\s*\d+$|^\d+\s*/\s*\d+$|^-\s*\d+\s*-$'
            )
            
            for line in lines:
                if page_number_pattern.match(line):
                    return 0.0  # 페이지 번호 발견 → FAIL
            
            # 2. 동일 단어 연속 반복 감지
            words = text.split()
            if len(words) >= 5:
                for i in range(len(words) - 4):
                    # 5개 연속 단어가 모두 같으면
                    if words[i] == words[i+1] == words[i+2] == words[i+3] == words[i+4]:
                        return 0.0  # 반복 노이즈 → FAIL
            
            # 3. 특수문자 비율 체크
            special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
            total_chars = len(text)
            
            if total_chars > 0:
                special_ratio = special_chars / total_chars
                if special_ratio > 0.30:  # 30% 이상이면 FAIL
                    return 0.0
            
            # 4. 숫자 전용 라인 비율
            digit_lines = sum(1 for line in lines if line.replace(' ', '').isdigit())
            digit_ratio = digit_lines / len(lines) if len(lines) > 0 else 0
            
            if digit_ratio > 0.30:  # 30% 이상이면 FAIL
                return 0.0
        
        return 1.0
    
    def evaluate_table_parsing(self, pages: List[Dict]) -> float:
        """
        table: 표 파싱 평가
        
        기준:
        - PASS (1.0):
          * 표가 없거나
          * 표가 있고 유효한 표가 50% 이상
        
        - FAIL (0.0):
          * 표가 있는데 유효한 표가 0개
          * 표 구조가 심각하게 깨짐
        
        유효한 표 조건:
          * 최소 2행 × 2열
          * 각 행의 컬럼 수가 일관적 (±1 허용)
          * 빈 셀 비율 ≤ 60%
        
        Returns:
            1.0 (Pass) or 0.0 (Fail)
        """
        
        total_tables = 0
        valid_tables = 0
        
        for page in pages:
            tables = page.get("tables", [])
            
            for table in tables:
                total_tables += 1
                
                # 표 유효성 체크
                rows = table.get("rows", 0)
                cols = table.get("cols", 0)
                data = table.get("data", [])
                
                # 최소 크기 체크
                if rows < 2 or cols < 2:
                    continue
                
                # 데이터 일관성
                if len(data) != rows:
                    continue
                
                # 각 행의 컬럼 수 일관성 (±1 허용)
                if len(data) > 0:
                    col_counts = [len(row) if isinstance(row, list) else 0 for row in data]
                    if len(col_counts) > 0:
                        col_diff = max(col_counts) - min(col_counts)
                        if col_diff > 1:
                            continue
                    
                    # 빈 셀 비율 (60% 이하)
                    total_cells = sum(col_counts)
                    if total_cells > 0:
                        empty_cells = sum(
                            1 for row in data 
                            for cell in (row if isinstance(row, list) else [])
                            if not str(cell).strip()
                        )
                        empty_ratio = empty_cells / total_cells
                        
                        if empty_ratio > 0.60:
                            continue
                
                valid_tables += 1
        
        # 표가 없으면 PASS (표가 필수는 아님)
        if total_tables == 0:
            return 1.0
        
        # 유효한 표 비율
        valid_ratio = valid_tables / total_tables
        
        # 50% 이상이면 PASS, 아니면 FAIL
        return 1.0 if valid_ratio >= 0.50 else 0.0
    
    # ===== 상세 정보 제공 메서드 (디버깅용) =====
    
    def get_detailed_check(self, pages: List[Dict]) -> Dict[str, Any]:
        """
        상세한 체크 결과 반환 (디버깅 및 로깅용)
        
        Returns:
            {
                'read': {'pass': True, 'reversal_ratio': 0.02, 'reason': ''},
                'sent': {'pass': True, 'avg_length': 45.2, 'ending_ratio': 0.85, 'reason': ''},
                'noise': {'pass': False, 'reason': 'Page number found'},
                'table': {'pass': True, 'valid_ratio': 0.75, 'reason': ''}
            }
        """
        
        result = {
            'read': self._check_reading_order_detailed(pages),
            'sent': self._check_sentence_detailed(pages),
            'noise': self._check_noise_detailed(pages),
            'table': self._check_table_detailed(pages)
        }
        
        return result
    
    def _check_reading_order_detailed(self, pages: List[Dict]) -> Dict:
        """읽기 순서 상세 체크"""
        if not pages or not pages[0].get("bbox"):
            return {'pass': True, 'reversal_ratio': 0.0, 'reason': 'No bbox data'}
        
        bbox_list = pages[0].get("bbox", [])
        if len(bbox_list) < 2:
            return {'pass': True, 'reversal_ratio': 0.0, 'reason': 'Too few bboxes'}
        
        reversals = 0
        prev_y = 0
        
        for bbox in bbox_list:
            y = bbox.get("y0", 0)
            if prev_y > 0 and y < prev_y - 10:
                reversals += 1
            prev_y = y
        
        reversal_ratio = reversals / len(bbox_list)
        passed = reversal_ratio < 0.05
        reason = f"{reversals} reversals ({reversal_ratio*100:.1f}%)" if not passed else ""
        
        return {'pass': passed, 'reversal_ratio': reversal_ratio, 'reason': reason}
    
    def _check_sentence_detailed(self, pages: List[Dict]) -> Dict:
        """문장 완결성 상세 체크"""
        full_text = " ".join([page.get("text", "") for page in pages]).strip()
        
        if len(full_text) < 50:
            return {'pass': False, 'reason': f'Text too short ({len(full_text)} chars)'}
        
        sentences = re.split(r'[.!?]+\s+|\n+', full_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return {'pass': False, 'reason': 'No sentences found'}
        
        avg_length = sum(len(s) for s in sentences) / len(sentences)
        
        if avg_length < 10:
            return {'pass': False, 'avg_length': avg_length, 'reason': 'Avg sentence too short'}
        
        if avg_length > 500:
            return {'pass': False, 'avg_length': avg_length, 'reason': 'Avg sentence too long'}
        
        sentence_endings = ['다', '요', '니다', '습니다', '음', '까', '네', '자', '.', '?', '!']
        ending_count = sum(1 for s in sentences if any(s.endswith(e) for e in sentence_endings))
        ending_ratio = ending_count / len(sentences)
        
        if ending_ratio < 0.30:
            return {'pass': False, 'avg_length': avg_length, 'ending_ratio': ending_ratio, 
                    'reason': 'Low ending ratio'}
        
        return {'pass': True, 'avg_length': avg_length, 'ending_ratio': ending_ratio, 'reason': ''}
    
    def _check_noise_detailed(self, pages: List[Dict]) -> Dict:
        """노이즈 제거 상세 체크"""
        for page in pages:
            text = page.get("text", "").strip()
            if not text:
                continue
            
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            
            # 페이지 번호
            page_number_pattern = re.compile(r'^\d{1,3}$|^페이지\s*\d+$|^\d+\s*/\s*\d+$')
            for line in lines:
                if page_number_pattern.match(line):
                    return {'pass': False, 'reason': f'Page number found: "{line}"'}
            
            # 연속 반복
            words = text.split()
            if len(words) >= 5:
                for i in range(len(words) - 4):
                    if words[i] == words[i+1] == words[i+2] == words[i+3] == words[i+4]:
                        return {'pass': False, 'reason': f'Repeated word: "{words[i]}"'}
            
            # 특수문자 비율
            special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
            special_ratio = special_chars / len(text) if len(text) > 0 else 0
            if special_ratio > 0.30:
                return {'pass': False, 'reason': f'High special char ratio: {special_ratio*100:.1f}%'}
            
            # 숫자 라인 비율
            digit_lines = sum(1 for line in lines if line.replace(' ', '').isdigit())
            digit_ratio = digit_lines / len(lines) if len(lines) > 0 else 0
            if digit_ratio > 0.30:
                return {'pass': False, 'reason': f'High digit line ratio: {digit_ratio*100:.1f}%'}
        
        return {'pass': True, 'reason': ''}
    
    def _check_table_detailed(self, pages: List[Dict]) -> Dict:
        """표 파싱 상세 체크"""
        total_tables = 0
        valid_tables = 0
        
        for page in pages:
            tables = page.get("tables", [])
            for table in tables:
                total_tables += 1
                rows = table.get("rows", 0)
                cols = table.get("cols", 0)
                
                if rows >= 2 and cols >= 2:
                    valid_tables += 1
        
        if total_tables == 0:
            return {'pass': True, 'valid_ratio': 1.0, 'reason': 'No tables (OK)'}
        
        valid_ratio = valid_tables / total_tables
        passed = valid_ratio >= 0.50
        reason = f"{valid_tables}/{total_tables} valid" if not passed else ""
        
        return {'pass': passed, 'valid_ratio': valid_ratio, 'reason': reason}


if __name__ == "__main__":
    # 테스트
    metrics = ValidationMetrics()
    print("[OK] ValidationMetrics initialized (Simple Yes/No)")
    
    # 테스트 데이터
    test_pages = [{
        "page": 1,
        "text": "이것은 테스트 문장입니다. 정상적인 문장 구조를 가지고 있습니다. 추가 문장도 있습니다.",
        "bbox": [
            {"text": "이것은", "x0": 0, "y0": 0, "x1": 50, "y1": 20},
            {"text": "테스트", "x0": 50, "y0": 0, "x1": 100, "y1": 20},
            {"text": "문장입니다", "x0": 100, "y0": 20, "x1": 200, "y1": 40}
        ],
        "tables": []
    }]
    
    print(f"\nSimple checks:")
    print(f"  read:  {metrics.evaluate_reading_order(test_pages)} (1.0=Pass, 0.0=Fail)")
    print(f"  sent:  {metrics.evaluate_sentence_integrity(test_pages)}")
    print(f"  noise: {metrics.evaluate_noise_removal(test_pages)}")
    print(f"  table: {metrics.evaluate_table_parsing(test_pages)}")
    
    print(f"\nDetailed checks:")
    details = metrics.get_detailed_check(test_pages)
    for axis, result in details.items():
        status = "PASS" if result['pass'] else "FAIL"
        print(f"  {axis}: [{status}] {result.get('reason', '')}")

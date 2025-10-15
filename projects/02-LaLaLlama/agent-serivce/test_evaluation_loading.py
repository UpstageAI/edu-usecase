#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# main_rag.py의 함수들을 임포트
from src.proposal_evaluator_flow.main_rag import load_evaluation_criteria

def test_evaluation_loading():
    """평가 기준 로딩 테스트"""
    print("=== 평가 기준 로딩 테스트 ===")
    
    # 테스트할 파일 경로들
    test_paths = [
        "./standard/evaluation.txt",
        "./standard/evaluaion.txt", 
        "./standard/evaluation_criteria.md"
    ]
    
    for path in test_paths:
        print(f"\n테스트 경로: {path}")
        print(f"파일 존재 여부: {os.path.exists(path)}")
        
        if os.path.exists(path):
            try:
                items = load_evaluation_criteria(path)
                print(f"로딩된 항목 수: {len(items)}")
                if items:
                    print(f"첫 번째 항목: {items[0]}")
                    print(f"대분류 목록: {set(item['대분류'] for item in items)}")
                else:
                    print("로딩된 항목이 없습니다.")
            except Exception as e:
                print(f"로딩 중 오류 발생: {e}")
        else:
            print("파일이 존재하지 않습니다.")

if __name__ == "__main__":
    test_evaluation_loading()

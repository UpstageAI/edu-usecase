import json

file_path = "preference_dataset.jsonl"
line_number = 0

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_number += 1
            # 각 줄을 JSON으로 파싱 시도
            json.loads(line)
    print(f"파일 '{file_path}'의 모든 라인({line_number}개)이 유효한 JSON 형식입니다.")

except json.JSONDecodeError as e:
    print(f"오류 발생! 파일: '{file_path}', 라인: {line_number}")
    print(f"오류 내용: {e}")
    print("해당 라인을 수정해주세요.")
except Exception as e:
    print(f"예상치 못한 오류 발생: {e}")

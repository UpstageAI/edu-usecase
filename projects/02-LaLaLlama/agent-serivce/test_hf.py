# test_hf.py

import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint

# 1. .env 파일에서 환경 변수를 불러옵니다.
load_dotenv()

print("--- Hugging Face API 연결 테스트 시작 ---")

# 2. .env 파일에서 HUGGINGFACEHUB_API_TOKEN을 제대로 읽어오는지 확인합니다.
api_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

if api_token:
    # 토큰의 일부만 출력하여 로딩 여부 확인 (보안을 위해 전체 토큰은 출력하지 않음)
    print(f"✅ API Token 로드 성공: '{api_token[:5]}...'")
else:
    print("❌ API Token 로드 실패! .env 파일을 확인해주세요.")
    # 토큰이 없으면 테스트를 중단합니다.
    exit()

try:
    # 3. LLM 객체를 생성합니다.
    print("\nLLM 객체 생성 시도...")
    llm = HuggingFaceEndpoint(
        repo_id="mistralai/Mistral-7B-Instruct-v0.2",
        huggingfacehub_api_token=api_token,
        temperature=0.1,
        max_new_tokens=1024
    )
    print("✅ LLM 객체 생성 성공!")

    # 4. LLM을 직접 호출하여 응답을 받아옵니다.
    print("\nLLM 호출 시도...")
    response = llm.invoke("Hi, how are you today?")
    print("✅ LLM 호출 성공!")
    print("\n--- LLM 응답 ---")
    print(response)
    print("\n--------------------")
    print("\n🎉 테스트 성공! API 키와 네트워크 연결에 문제가 없습니다.")

except Exception as e:
    print("\n❌ 테스트 실패!")
    print("--- 발생한 에러 ---")
    print(e)
    print("\n--------------------")
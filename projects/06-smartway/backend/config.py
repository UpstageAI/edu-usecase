"""
Backend Configuration

환경 변수 및 LLM 설정
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# .env 파일 로드
load_dotenv()

# API Keys
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def build_chat_model(model: str = "solar-pro", temperature: float = 0.7):
    """
    LLM 인스턴스 생성

    Args:
        model (str): 모델 이름 ("solar-pro" | "solar-pro2")
        temperature (float): Temperature 설정 (0.0 ~ 1.0)

    Returns:
        ChatOpenAI: LLM 인스턴스
    """
    if model == "solar-pro2":
        return ChatOpenAI(
            model="solar-pro2",
            api_key=UPSTAGE_API_KEY,
            base_url="https://api.upstage.ai/v1/solar",
            temperature=temperature
        )

    return ChatOpenAI(
        model="solar-pro",
        api_key=UPSTAGE_API_KEY,
        base_url="https://api.upstage.ai/v1/solar",
        temperature=temperature
    )

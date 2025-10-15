#!/usr/bin/env python3
"""
Fine-tuned GGUF 모델을 사용하는 LlamaLocalClient 구현
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False
    logger.warning("llama-cpp-python not installed. LlamaGGUFClient will not work.")


class LlamaGGUFClient:
    """
    Fine-tuned GGUF 모델 로더 (llama.cpp 기반)

    Args:
        model_path: GGUF 파일 경로
        n_ctx: Context length (기본: 2048)
        n_gpu_layers: GPU에 올릴 레이어 수 (기본: -1 = 전부)
        temperature: 생성 온도 (기본: 0.1)
        max_tokens: 최대 생성 토큰 (기본: 512)
        verbose: 로깅 출력 (기본: False)
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 2048,
        n_gpu_layers: int = -1,
        temperature: float = 0.1,
        max_tokens: int = 512,
        verbose: bool = False,
    ):
        if not HAS_LLAMA_CPP:
            raise ImportError("llama-cpp-python is required. Install with: pip install llama-cpp-python")

        # 기본 모델 경로: fine-tuned term normalizer
        if model_path is None:
            # 프로젝트 루트에서 models/ 폴더 찾기
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent  # ctdmate/brain/llama_client.py -> CTDMate/
            default_model = project_root / "models" / "llama-3.2-3B-term-normalizer-F16.gguf"

            if default_model.exists():
                model_path = str(default_model)
                logger.info(f"Using default fine-tuned model: {model_path}")
            else:
                raise FileNotFoundError(
                    f"Default model not found: {default_model}\n"
                    f"Please specify model_path or place the GGUF file at: {default_model}"
                )

        model_path_obj = Path(model_path)
        if not model_path_obj.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        self.model_path = str(model_path_obj)
        self.temperature = temperature
        self.max_tokens = max_tokens

        logger.info(f"Loading GGUF model: {self.model_path}")
        logger.info(f"  n_ctx: {n_ctx}, n_gpu_layers: {n_gpu_layers}")

        # Llama 모델 로드
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=verbose,
        )

        logger.info(f"✓ Model loaded successfully")

    def chat(self, system: str, user: str) -> str:
        """
        Chat completion (Llama3 형식)

        Args:
            system: System prompt
            user: User message

        Returns:
            Model response (string)
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        response = self.llm.create_chat_completion(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # Extract response text
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip()

    def __call__(self, prompt: str, **kwargs) -> str:
        """
        Direct prompt completion (system=없이 사용)

        Args:
            prompt: Prompt text
            **kwargs: Override temperature, max_tokens, etc.

        Returns:
            Model response
        """
        temp = kwargs.get("temperature", self.temperature)
        max_tok = kwargs.get("max_tokens", self.max_tokens)

        response = self.llm(
            prompt,
            temperature=temp,
            max_tokens=max_tok,
            echo=False,
        )

        return response.get("choices", [{}])[0].get("text", "").strip()


def create_default_client(**kwargs) -> LlamaGGUFClient:
    """
    기본 fine-tuned 모델로 클라이언트 생성

    Args:
        **kwargs: LlamaGGUFClient에 전달할 인자

    Returns:
        LlamaGGUFClient 인스턴스
    """
    return LlamaGGUFClient(**kwargs)


# Alias for backward compatibility
LlamaLocalClient = LlamaGGUFClient


if __name__ == "__main__":
    # 테스트
    import logging
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("Testing LlamaGGUFClient with fine-tuned model")
    print("=" * 80)

    # 클라이언트 생성
    client = create_default_client(verbose=True)

    # Chat 테스트
    system_prompt = "You are a pharmaceutical terminology expert. Normalize medical terms."
    user_input = "정제수, 프로필렌글리콜, 에탄올"

    print(f"\nSystem: {system_prompt}")
    print(f"User: {user_input}")
    print("\nResponse:")

    response = client.chat(system_prompt, user_input)
    print(response)

    print("\n" + "=" * 80)
    print("Test completed")
    print("=" * 80)

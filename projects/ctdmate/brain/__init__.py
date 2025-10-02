# ctdmate/brain/__init__.py
from __future__ import annotations
from .router import Router, LlamaLocalClient

# Fine-tuned GGUF 모델 클라이언트
try:
    from .llama_client import LlamaGGUFClient, create_default_client
    __all__ = ["Router", "LlamaLocalClient", "LlamaGGUFClient", "create_default_client"]
except ImportError:
    # llama-cpp-python이 없으면 기본 클라이언트만 export
    __all__ = ["Router", "LlamaLocalClient"]

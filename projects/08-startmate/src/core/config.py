from pydantic import BaseModel
import os

class Settings(BaseModel):
    # --- LLM Provider 선택 (외부 API/로컬 전환 지원) ---
    model_provider: str = (os.getenv("MODEL_PROVIDER", os.getenv("LLM_PROVIDER", "upstage")) or "upstage").lower()

    # Upstage (외부 API)
    upstage_api_key: str | None = os.getenv("UPSTAGE_API_KEY")
    upstage_base: str = os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1")
    upstage_model: str = os.getenv("UPSTAGE_MODEL", "solar-pro-2")

    # OpenAI-호환 외부 API (선택)
    llm_api_key: str | None = os.getenv("LLM_API_KEY")
    llm_api_base: str = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # 로컬 LLM (옵션)
    infer_url: str = os.getenv("INFER_URL", os.getenv("LOCAL_LLM_BASE", "http://local-llm:8000"))
    infer_model: str = os.getenv("INFER_MODEL", os.getenv("LOCAL_LLM_MODEL", "llama-3.2-3b-instruct"))

    # 임베딩 서버 (클라우드 사용 전제)
    embed_base: str = os.getenv("EMBED_URL", os.getenv("EMBED_BASE_URL", ""))  # 클라우드 URL 필수 권장
    embed_model: str | None = os.getenv("EMBED_MODEL")
    embed_api_key: str | None = os.getenv("EMBED_API_KEY")  # ← 클라우드 인증 토큰(있으면 헤더로 전송)
    embed_max_batch: int = int(os.getenv("EMBED_MAX_BATCH", "128"))

    # Qdrant (클라우드)
    qdrant_url: str | None = os.getenv("QDRANT_URL")  # 예: https://xxxxxxxx.aws.cloud.qdrant.io
    qdrant_key: str | None = os.getenv("QDRANT_API_KEY")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "patent_db")

    class Config:
        frozen = False
        arbitrary_types_allowed = True

    @property
    def llm_provider(self) -> str:  # 호환 alias
        return self.model_provider

settings = Settings()

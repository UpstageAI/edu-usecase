import os, math, requests
from typing import Iterable

class EmbeddingClient:
    def __init__(self):
        self.url = os.getenv("EMBED_URL")
        if not self.url:
            raise RuntimeError("EMBED_URL not set")
        self.api_key = os.getenv("EMBED_API_KEY") or ""
        self.max_batch = int(os.getenv("EMBED_MAX_BATCH", "64"))

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _post(self, payload: dict):
        r = requests.post(self.url, json=payload, headers=self._headers(), timeout=30)
        if r.status_code >= 400:
            raise requests.HTTPError(f"{r.status_code} {r.text}", response=r)
        return r.json()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        if not texts:
            return out
        bsz = max(1, self.max_batch)
        for i in range(0, len(texts), bsz):
            chunk = texts[i:i+bsz]
            data = self._post({"texts": chunk})
            # 기본(FastAPI) 스펙
            if "embeddings" in data:
                out.extend(data["embeddings"])
                continue
            # OpenAI 호환 응답 스펙도 지원
            if "data" in data and data["data"] and "embedding" in data["data"][0]:
                out.extend([d["embedding"] for d in data["data"]])
                continue
            raise ValueError(f"Unexpected embedding response shape: {data.keys()}")
        return out

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

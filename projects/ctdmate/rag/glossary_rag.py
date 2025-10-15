# ctdmate/rag/glossary_rag.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
import os

# Qdrant 클라이언트(선택)
try:
    from qdrant_client import QdrantClient, models
except Exception:
    QdrantClient = None  # type: ignore
    models = None  # type: ignore

# FastEmbed(e5) 임베더(선택)
try:
    from fastembed import TextEmbedding
except Exception:
    TextEmbedding = None  # type: ignore

DEFAULT_COLLECTION = os.getenv("QDRANT_GLOSSARY_COLLECTION", "glossary")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/e5-large-v2")

def _e5_query_prefix(q: str) -> str:
    return f"query: {q}"

class _DummyEmbedder:
    def embed(self, texts: List[str]) -> List[List[float]]:
        import numpy as np, hashlib
        vecs: List[List[float]] = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            arr = np.frombuffer(h, dtype=np.uint8).astype("float32")
            arr = arr[:64] if arr.size >= 64 else np.pad(arr, (0, 64-arr.size))
            vecs.append((arr / max(1.0, float(np.linalg.norm(arr)))).tolist())
        return vecs

def _build_embedder():
    if TextEmbedding:
        try:
            return TextEmbedding(model_name=EMBED_MODEL)
        except Exception:
            pass
    return _DummyEmbedder()

class GlossaryRAGTool:
    """
    용어집 RAG 검색기.
    - Qdrant 컬렉션에서 term/definition/synonyms 검색
    - 반환 포맷: {"content": str, "metadata": {...}, "score": float}
    """
    def __init__(
        self,
        collection: Optional[str] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        top_k: int = 5
    ):
        self.collection = collection or DEFAULT_COLLECTION
        self.top_k = int(top_k)
        self.client = None

        if QdrantClient:
            try:
                qdrant_url = url or QDRANT_URL
                qdrant_api_key = api_key or QDRANT_API_KEY

                # 로컬 디렉토리 모드 우선
                if not qdrant_url or qdrant_url == "":
                    from pathlib import Path
                    storage_path = Path("qdrant_storage") / "glossary"
                    self.client = QdrantClient(path=str(storage_path))
                else:
                    self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)
            except Exception:
                self.client = None

        self.embedder = _build_embedder()

    def search(self, query: str, k: Optional[int] = None) -> List[Dict[str, Any]]:
        k = k or self.top_k
        if not self.client:
            return []
        qv = self.embedder.embed([_e5_query_prefix(query)])[0]
        try:
            res = self.client.search(
                collection_name=self.collection,
                query_vector=qv,
                limit=k,
                with_payload=True,
                with_vectors=False,
            )
        except Exception:
            return []
        out: List[Dict[str, Any]] = []
        for p in res or []:
            pl = p.payload or {}
            out.append({
                "content": pl.get("text") or pl.get("definition") or "",
                "metadata": {
                    "source": pl.get("source") or "glossary",
                    "module": pl.get("module") or "GENERAL",
                    "page": pl.get("page"),
                    "term": pl.get("term") or pl.get("title"),
                    "synonyms": pl.get("synonyms"),
                },
                "score": float(p.score or 0.0),
            })
        return out

    def lookup_term(self, term: str) -> Optional[Dict[str, Any]]:
        hits = self.search(term, k=1)
        return hits[0] if hits else None

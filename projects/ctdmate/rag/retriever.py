# ctdmate/rag/retriever.py
from __future__ import annotations
import os, json, math, hashlib
from typing import List, Dict, Any, Optional, Iterable, Tuple
from pathlib import Path

# ---- config ----
try:
    from ctdmate.app import config as CFG
except Exception:
    from ..app import config as CFG  # type: ignore

# ---- deps (soft) ----
try:
    from qdrant_client import QdrantClient, models
except Exception as e:
    QdrantClient = None  # type: ignore
    models = None  # type: ignore
    _qdrant_import_error = e

try:
    from fastembed import TextEmbedding
except Exception as e:
    TextEmbedding = None  # type: ignore
    _fastembed_import_error = e

try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    SentenceTransformer = None  # type: ignore
    _sentence_transformers_import_error = e

try:
    from rank_bm25 import BM25Okapi  # optional
except Exception:
    BM25Okapi = None  # type: ignore

import numpy as np
import re

E5_QUERY_PREFIX = os.getenv("E5_QUERY_PREFIX", "query: ")
E5_DOC_PREFIX   = os.getenv("E5_DOC_PREFIX",   "passage: ")

def _norm_text(s: str) -> str:
    return " ".join((s or "").split())

def _tokens_for_bm25(s: str) -> List[str]:
    return re.findall(r"[A-Za-z가-힣0-9]{2,}", s.lower())

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0

def _build_embedder():
    # Try sentence-transformers first (supports more models including -instruct variants)
    if SentenceTransformer:
        try:
            model = SentenceTransformer(CFG.EMBED_MODEL)
            # Wrap to match FastEmbed API
            class _STWrapper:
                def __init__(self, model):
                    self.model = model
                def embed(self, texts: List[str]) -> List[List[float]]:
                    return self.model.encode(texts, convert_to_numpy=True).tolist()
            return _STWrapper(model)
        except Exception as e:
            import sys
            print(f"[WARNING] SentenceTransformer failed: {e}", file=sys.stderr)

    # Fallback to FastEmbed
    if TextEmbedding:
        try:
            return TextEmbedding(model_name=CFG.EMBED_MODEL)
        except Exception as e:
            import sys
            print(f"[WARNING] FastEmbed failed: {e}", file=sys.stderr)

    # very small deterministic fallback
    import sys
    print(f"[WARNING] Using dummy embedder (256 dims)", file=sys.stderr)
    class _Dummy:
        def embed(self, texts: List[str]) -> List[List[float]]:
            vecs = []
            for t in texts:
                h = hashlib.sha256(t.encode("utf-8")).digest()
                arr = np.frombuffer(h, dtype=np.uint8).astype("float32")
                arr = arr[:256] if arr.size >= 256 else np.pad(arr, (0, 256-arr.size))
                v = arr / max(1.0, float(np.linalg.norm(arr)))
                vecs.append(v.tolist())
            return vecs
    return _Dummy()

def _ensure_qdrant():
    if QdrantClient is None or models is None:
        raise RuntimeError(f"qdrant-client 미설치: {getattr(globals(),'_qdrant_import_error',None)}")

class Retriever:
    """
    Qdrant 컬렉션 검색기.
    - vector_search: 벡터 kNN
    - search_hybrid: 벡터(kNN) 후보 → BM25 재랭크 → alpha 결합
    - mmr_rerank: 다양성 재랭크
    반환 포맷: {"content": str, "metadata": {...}, "score": float}
    """
    def __init__(
        self,
        collection: Optional[str] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        use_bm25: bool = True,
        fetch_payload_text_key: str = "text",
    ):
        _ensure_qdrant()
        self.collection = collection or CFG.QDRANT_GUIDE_COLLECTION

        # Qdrant 클라이언트 초기화 (로컬 path 모드 우선)
        qdrant_url = url or CFG.QDRANT_URL
        qdrant_api_key = api_key or CFG.QDRANT_API_KEY

        if not qdrant_url or qdrant_url == "":
            # 로컬 디렉토리 모드 (collection 기반 경로)
            from pathlib import Path
            # Use collection name to determine storage path
            if self.collection == "combined_regulations":
                storage_path = Path("qdrant_storage") / "regulations"
            elif self.collection == "glossary" or self.collection == "glossary_terms":
                storage_path = Path("qdrant_storage") / "glossary"
            elif self.collection in ("mfds_guidelines", "guidelines"):
                # MFDS와 guidelines 모두 같은 storage 사용
                storage_path = Path("qdrant_storage") / "mfds"
            elif self.collection == "ich":
                storage_path = Path("qdrant_storage") / "ich"
            else:
                # 기타: collection 이름을 그대로 사용
                storage_path = Path("qdrant_storage") / self.collection
            self.client = QdrantClient(path=str(storage_path))
        else:
            # 서버 모드 (HTTP/HTTPS)
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)

        self.embedder = _build_embedder()
        self.use_bm25 = bool(use_bm25 and BM25Okapi is not None)
        self.payload_key = fetch_payload_text_key

    # ---------- Qdrant Filter ----------
    def _build_filter(self, where: Optional[Dict[str, Any]]) -> Optional["models.Filter"]:
        if not where:
            return None
        must: List["models.FieldCondition"] = []
        rngs: List["models.Range"] = []
        for k, v in where.items():
            if v is None:
                continue
            if isinstance(v, dict) and any(x in v for x in ("gte","lte","gt","lt")):
                rng = models.Range(
                    gte=v.get("gte"), lte=v.get("lte"),
                    gt=v.get("gt"), lt=v.get("lt")
                )
                must.append(models.FieldCondition(key=k, range=rng))
            elif isinstance(v, (list, tuple, set)):
                must.append(models.FieldCondition(key=k, match=models.MatchAny(any=list(v))))
            else:
                must.append(models.FieldCondition(key=k, match=models.MatchValue(value=v)))
        return models.Filter(must=must) if must else None

    # ---------- Vector search ----------
    def vector_search(
        self, query: str, k: int = 5, where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        qv = self.embedder.embed([E5_QUERY_PREFIX + _norm_text(query)])[0]
        flt = self._build_filter(where)
        try:
            res = self.client.search(
                collection_name=self.collection,
                query_vector=qv,
                limit=int(k),
                with_payload=True,
                with_vectors=False,
                query_filter=flt,
            )
        except Exception:
            return []
        return [self._point_to_doc(p) for p in res or []]

    # ---------- Hybrid (vector + BM25) ----------
    def search_hybrid(
        self,
        query: str,
        k: int = 5,
        fetch_k: int = 30,
        alpha: float = 0.7,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        alpha = float(alpha)
        fetch_k = max(k, int(fetch_k))
        # Step1: vector fetch_k
        vec_hits = self.vector_search(query, k=fetch_k, where=where)
        if not vec_hits:
            return []
        if not self.use_bm25:
            return vec_hits[:k]

        # Step2: BM25 on fetched docs
        texts = [d.get("content") or "" for d in vec_hits]
        tokenized = [_tokens_for_bm25(t) for t in texts]
        bm = BM25Okapi(tokenized)  # type: ignore
        bm_scores = bm.get_scores(_tokens_for_bm25(query))  # type: ignore

        # Step3: Normalize and combine
        vec_scores = np.array([float(d.get("score", 0.0)) for d in vec_hits], dtype="float32")
        def _norm(x: np.ndarray) -> np.ndarray:
            if x.size == 0: return x
            mn, mx = float(x.min()), float(x.max())
            return (x - mn) / (mx - mn) if mx > mn else np.zeros_like(x)
        vnorm = _norm(vec_scores)
        bnorm = _norm(np.array(bm_scores, dtype="float32"))

        comb = alpha * vnorm + (1.0 - alpha) * bnorm
        order = np.argsort(-comb)
        ranked = [vec_hits[i] | {"score": float(comb[i])} for i in order[:k]]
        return ranked

    # ---------- MMR rerank ----------
    def mmr_rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        k: int = 5,
        lambda_mult: float = 0.5,
        text_key: str = "content",
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        q_vec = np.array(self.embedder.embed([E5_QUERY_PREFIX + _norm_text(query)])[0], dtype="float32")
        docs = [c.get(text_key) or "" for c in candidates]
        dvecs = np.array(self.embedder.embed([E5_DOC_PREFIX + _norm_text(t) for t in docs]), dtype="float32")

        sims_to_q = np.array([_cosine(q_vec, v) for v in dvecs], dtype="float32")
        selected: List[int] = []
        remaining: List[int] = list(range(len(candidates)))

        while remaining and len(selected) < k:
            if not selected:
                i = int(np.argmax(sims_to_q[remaining]))
                selected.append(remaining.pop(i))
                continue
            best_idx = None
            best_score = -math.inf
            for idx_pos, idx in enumerate(remaining):
                max_div = 0.0
                for s in selected:
                    max_div = max(max_div, _cosine(dvecs[idx], dvecs[s]))
                score = lambda_mult * sims_to_q[idx] - (1.0 - lambda_mult) * max_div
                if score > best_score:
                    best_score = score
                    best_idx = idx_pos
            selected.append(remaining.pop(best_idx))  # type: ignore
        return [candidates[i] for i in selected[:k]]

    # ---------- Helpers ----------
    def _point_to_doc(self, p) -> Dict[str, Any]:
        pl = p.payload or {}

        # Content 추출: page_content (LangChain 스타일) 또는 self.payload_key 또는 definition
        content = pl.get("page_content") or pl.get(self.payload_key) or pl.get("definition") or ""

        # Metadata 추출: metadata 객체가 있으면 사용, 없으면 root level에서 추출
        if "metadata" in pl and isinstance(pl["metadata"], dict):
            meta = pl["metadata"]
        else:
            meta = pl

        return {
            "content": content,
            "metadata": {
                "source": meta.get("source") or meta.get("file_name"),
                "module": meta.get("module") or "GENERAL",
                "page": meta.get("page"),
                "section": meta.get("section"),
                "heading": meta.get("heading"),
                "heading_level": meta.get("heading_level"),
                "region": meta.get("region"),
                "title": meta.get("title"),
                "keywords": meta.get("keywords"),
                "para_id": meta.get("para_id"),
            },
            "score": float(getattr(p, "score", 0.0) or 0.0),
        }

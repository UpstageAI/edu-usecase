from __future__ import annotations

import os
from typing import Iterable, Optional

from pydantic import BaseModel, Field, PrivateAttr, ConfigDict
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from .config import settings


# ---------------------- helpers ---------------------- #

def _take(n: int, it: Iterable[object]):
    i = 0
    for x in it:
        if i >= n:
            break
        yield x
        i += 1


def _build_snippet(payload: dict[str, object]) -> str:
    """
    Make a short preview text from payload.
    Preference: claims > abstract > text > title
    """
    text = (
        payload.get("claims")
        or payload.get("abstract")
        or payload.get("text")
        or payload.get("title")
        or ""
    )
    if not isinstance(text, str):
        text = str(text)
    return (text[:240] + "…") if len(text) > 240 else text


# ---------------------- store ------------------------ #

class QdrantStore(BaseModel):
    """
    Qdrant wrapper used by RAG retriever.

    Supports single-collection and multi-collection search.

    Defaults (via settings / env):
      - settings.qdrant_url        ← QDRANT_URL (default: http://qdrant:6333)
      - settings.qdrant_key        ← QDRANT_API_KEY (optional)
      - settings.qdrant_collection ← QDRANT_COLLECTION (default: patent_db)

    You can pass `collections=["ipraw_db","patent_db"]` at init time to
    search multiple collections (use `k_each` in search()).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: Optional[str] = Field(
        default_factory=lambda: getattr(settings, "qdrant_url", None)
        or os.getenv("QDRANT_URL", "http://qdrant:6333")
    )
    key: Optional[str] = Field(
        default_factory=lambda: getattr(settings, "qdrant_key", None)
        or (os.getenv("QDRANT_API_KEY") or None)
    )
    collection: str = Field(
        default_factory=lambda: getattr(settings, "qdrant_collection", None)
        or os.getenv("QDRANT_COLLECTION", "patent_db")
    )
    collections: Optional[list[str]] = None  # multi-collection mode if provided

    _client: QdrantClient | None = PrivateAttr(default=None)

    def __init__(self, **data: object):
        super().__init__(**data)
        self._client = QdrantClient(url=self.url, api_key=self.key)

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=self.url, api_key=self.key)
        return self._client

    # --------------------------- core search --------------------------------- #

    def _search_one(
        self,
        collection: str,
        vector: list[float],
        *,
        limit: int,
        qfilter: Optional[qm.Filter] = None,
        with_payload: bool = True,
    ) -> list[qm.ScoredPoint]:
        return self.client.search(
            collection_name=collection,
            query_vector=vector,
            limit=limit,
            with_payload=with_payload,
            query_filter=qfilter,
        )

    def _normalize_hit(self, h: qm.ScoredPoint, collection: str) -> dict[str, object]:
        pl = dict(h.payload or {})
        title = pl.get("title") or pl.get("invention_title") or ""
        return {
            "collection": collection,
            "id": h.id,
            "score": float(h.score or 0.0),
            "title": title,
            "documentId": pl.get("documentId"),
            "open_date": pl.get("open_date"),
            "register_date": pl.get("register_date"),
            "application_date": pl.get("application_date"),
            "snippet": _build_snippet(pl),
            "meta": pl,
        }

    # --------------------------- public API ---------------------------------- #

    def search(
        self,
        vector: list[float],
        *,
        limit: int = 8,
        qfilter: Optional[qm.Filter] = None,
        k_each: Optional[int] = None,
        interleave: bool = False,
    ) -> list[dict[str, object]]:
        """
        Search either a single collection (default) or multiple collections.

        Args:
            vector: query embedding
            limit: max results for single-collection mode
            qfilter: optional qm.Filter (date range, etc.)
            k_each: when `collections` is provided, number of hits per collection (default 5)
            interleave: if True (multi mode), results are interleaved by score; otherwise
                        kept grouped by collection (each with k_each)
        Returns:
            list of normalized dicts.
        """
        cols = self.collections or [self.collection]

        # single collection path
        if len(cols) == 1:
            hits = self._search_one(cols[0], vector, limit=limit, qfilter=qfilter)
            return [self._normalize_hit(h, cols[0]) for h in hits]

        # multi-collection path
        k = k_each or 5
        blocks: list[list[dict[str, object]]] = []
        for col in cols:
            try:
                hits = self._search_one(col, vector, limit=k, qfilter=qfilter)
            except Exception as e:
                print(f"[warn] search failed on {col}: {e}")
                hits = []
            blocks.append([self._normalize_hit(h, col) for h in hits])

        if not interleave:
            merged: list[dict[str, object]] = []
            for b in blocks:
                merged.extend(b)
            return merged[:limit] if limit else merged

        # interleave by score
        cursors = [iter(b) for b in blocks]
        heads = [next(c, None) for c in cursors]
        out: list[dict[str, object]] = []
        while any(h is not None for h in heads):
            best_idx = None
            best_score = float("-inf")
            for i, h in enumerate(heads):
                if h is not None and h["score"] > best_score:
                    best_idx = i
                    best_score = h["score"]
            out.append(heads[best_idx])
            heads[best_idx] = next(cursors[best_idx], None)
            if limit and len(out) >= limit:
                break
        return out

# ctdmate/rag/mfds_rag.py
from __future__ import annotations
import os, yaml
from typing import List, Dict, Any, Optional

# config
try:
    from ctdmate.app import config as CFG
except Exception:
    from ..app import config as CFG  # type: ignore

# base retriever
try:
    from ctdmate.rag.retriever import Retriever
except Exception:
    from .retriever import Retriever  # type: ignore

HYBRID_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.7"))  # 벡터:BM25 가중

def _normalize_section(s: str) -> str:
    s = (s or "").strip().upper()
    return s if s.startswith("M") else f"M{s}"

def _load_yaml(path: str | None) -> dict:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

class MFDSRAGTool:
    """
    MFDS/ICH 가이드라인 전용 RAG.
    - 컬렉션: CFG.QDRANT_GUIDE_COLLECTION
    - search_by_module: 모듈 필터 + 하이브리드
    - search_with_mmr: 하이브리드 결과를 MMR 다양성 재랭크
    """
    def __init__(
        self,
        collection: Optional[str] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        use_bm25: bool = False,  # BM25 disabled by default (causes issues with filters)
    ):
        # Default to mfds_guidelines (actual collection name in qdrant_storage/mfds/)
        self.collection = collection or "mfds_guidelines"
        self.retriever = Retriever(collection=self.collection, url=url, api_key=api_key, use_bm25=use_bm25)
        # 선택적 필터 규칙(rules/rag_filters.yaml)
        self.filter_rules = _load_yaml(str(CFG.RULES_DIR / "rag_filters.yaml"))

    def _where_for_module(self, module: str) -> Dict[str, Any]:
        m = _normalize_section(module)
        # Use nested path for metadata (LangChain-style payload)
        where: Dict[str, Any] = {"metadata.module": m}
        # YAML에 region/source 제한이 있으면 병합
        mod_rules = (self.filter_rules.get("modules", {}) or {}).get(m, {})
        if isinstance(mod_rules, dict):
            for k in ("region", "source", "section"):
                v = mod_rules.get(k)
                if v:
                    where[k] = v
        # 전역 필터
        global_where = self.filter_rules.get("global", {})
        if isinstance(global_where, dict):
            for k, v in global_where.items():
                where.setdefault(k, v)
        return where

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        # Use vector_search when BM25 is disabled
        if not self.retriever.use_bm25:
            return self.retriever.vector_search(query=query, k=k)
        return self.retriever.search_hybrid(query=query, k=k, fetch_k=max(20, 4*k), alpha=HYBRID_ALPHA)

    def search_by_module(self, query: str, module: str, k: int = 5) -> List[Dict[str, Any]]:
        where = self._where_for_module(module)
        # Use vector_search when BM25 is disabled
        if not self.retriever.use_bm25:
            return self.retriever.vector_search(query=query, k=k, where=where)
        return self.retriever.search_hybrid(query=query, k=k, fetch_k=max(20, 4*k), alpha=HYBRID_ALPHA, where=where)

    def search_with_mmr(
        self,
        query: str,
        k: int = 5,
        fetch_k: int = 30,
        lambda_mult: float = 0.5,
        module: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        where = self._where_for_module(module) if module else None
        cands = self.retriever.search_hybrid(query=query, k=fetch_k, fetch_k=fetch_k, alpha=HYBRID_ALPHA, where=where)
        return self.retriever.mmr_rerank(query=query, candidates=cands, k=k, lambda_mult=lambda_mult)

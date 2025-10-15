# src/graph/nodes/retrieve.py
from __future__ import annotations

import os
from typing import Optional

from qdrant_client.http import models as qm

from core.utils import Timer
from core.embed_client import EmbeddingClient
from core.qdrant_store import QdrantStore
from core.schemas import Doc


# ---- module singletons ------------------------------------------------------

# 외부 임베딩 API 사용 (EMBED_URL, EMBED_API_KEY, EMBED_MAX_BATCH 기반)
_emb = EmbeddingClient()

# QdrantStore는 .env 의 QDRANT_COLLECTIONS=colA,colB 가 있으면 멀티 모드로 동작하도록 구현되어 있다고 가정
_qds = QdrantStore()


# ---- helpers ----------------------------------------------------------------

def _state_get_extra(state) -> dict:
    """
    우선순위:
      1) state.route.extra (일반적인 경로)
      2) state.extra       (임시/실험용 필드가 있을 수 있음)
    """
    extra = {}
    try:
        if getattr(state, "route", None) and getattr(state.route, "extra", None):
            if isinstance(state.route.extra, dict):
                extra.update(state.route.extra)
    except Exception:
        pass
    try:
        if getattr(state, "extra", None) and isinstance(state.extra, dict):
            extra.update(state.extra)
    except Exception:
        pass
    return extra


def _to_int(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except Exception:
        return None


def _build_filter(extra: dict) -> Optional[qm.Filter]:
    """
    extra 로부터 Qdrant 필터 구성.
    - IPC: ipc_main / ipc_class / ipc_subclass
    - 연도: open_year_*, application_year_*, register_year_* (정수)
    """
    must: list[qm.Condition] = []

    # IPC 매칭
    ipc_main = extra.get("ipc_main")
    if ipc_main:
        must.append(qm.FieldCondition(key="ipc_main", match=qm.MatchValue(value=str(ipc_main))))

    ipc_class = extra.get("ipc_class")
    if ipc_class:
        must.append(qm.FieldCondition(key="ipc_class", match=qm.MatchValue(value=str(ipc_class))))

    ipc_subclass = extra.get("ipc_subclass")
    if ipc_subclass:
        must.append(qm.FieldCondition(key="ipc_subclass", match=qm.MatchValue(value=str(ipc_subclass))))

    # 연도 범위들
    def _yr_range(prefix: str, field: str):
        gte = _to_int(extra.get(f"{prefix}_gte"))
        lte = _to_int(extra.get(f"{prefix}_lte"))
        if gte is None and lte is None:
            return
        rng = qm.Range()
        if gte is not None:
            rng.gte = gte
        if lte is not None:
            rng.lte = lte
        must.append(qm.FieldCondition(key=field, range=rng))

    _yr_range("open_year", "open_year")
    _yr_range("application_year", "application_year")
    _yr_range("register_year", "register_year")

    return qm.Filter(must=must) if must else None


def _build_ctx_from_docs(docs: list[Doc], max_chars: int = 4000) -> str:
    """
    상위 문서들의 본문(text) 위주로 컨텍스트 구성.
    너무 길어지면 max_chars 근처에서 잘라냄.
    """
    parts = []
    total = 0
    for d in docs:
        t = (d.text or "").strip()
        if not t:
            continue
        # 한 문서당 간단 헤더 포함
        header = f"[{d.title or d.id or ''}] (score={d.score:.4f})"
        block = f"{header}\n{t}\n"
        if total + len(block) > max_chars:
            remain = max_chars - total
            if remain > 0:
                parts.append(block[:remain])
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts)


# ---- nodes ------------------------------------------------------------------

def node_retrieve_embed(state):
    """
    1) state.query → 임베딩
    2) state.query_vector 저장
    3) timings/debug 기록
    """
    query = getattr(state, "query", None)
    if not query or not isinstance(query, str):
        # 조회할 질의가 없으면 스킵
        dbg = dict(getattr(state, "debug", {}) or {})
        dbg["retrieve_skip"] = "no_query"
        state.debug = dbg
        return state

    with Timer() as t:
        try:
            vec = _emb.embed(query)
        except Exception as e:
            dbg = dict(getattr(state, "debug", {}) or {})
            dbg["retrieve_skip"] = f"embed_error: {e}"
            state.debug = dbg
            return state

    # 타이밍 기록
    timings = dict(getattr(state, "timings", {}) or {})
    timings["embed_ms"] = t.ms
    state.timings = timings

    # 벡터 검증
    if not isinstance(vec, list) or not vec or not isinstance(vec[0], (int, float)):
        dbg = dict(getattr(state, "debug", {}) or {})
        dbg["retrieve_skip"] = "no_vector"
        state.debug = dbg
        return state

    state.query_vector = vec
    # 디버그
    dbg = dict(getattr(state, "debug", {}) or {})
    dbg["embed_dim"] = len(vec)
    state.debug = dbg
    return state


def node_retrieve_ctx(state):
    """
    1) state.query_vector 로 Qdrant 검색
    2) 멀티 컬렉션: QDRANT_COLLECTIONS 기반 자동 (QdrantStore 내부에서 처리되었다고 가정)
    3) hits → Doc 변환하여 state.docs에 저장
    4) 상위 Doc로 ctx 문자열 생성(state.ctx)
    5) timings/debug 기록
    """
    vector = getattr(state, "query_vector", None)
    if not vector:
        # 임베딩이 없으면 스킵
        return state

    extra = _state_get_extra(state)

    # 파라미터 우선순위: state.extra/route.extra > ENV > 디폴트
    limit = _to_int(extra.get("limit")) or _to_int(os.getenv("RAG_K")) or 8

    # 멀티 컬렉션 여부(QdrantStore 내부가 ENV를 이미 반영했다고 가정)
    multi = bool(getattr(_qds, "collections", None)) and len(_qds.collections) >= 2

    interleave = bool(extra.get("interleave", True if multi else False))
    k_each = _to_int(extra.get("k_each")) or (_to_int(os.getenv("RAG_K_EACH")) or 4 if multi else None)

    qfilter = _build_filter(extra)

    with Timer() as t:
        try:
            hits = _qds.search(
                vector=vector,
                limit=limit,
                qfilter=qfilter,
                k_each=k_each,
                interleave=interleave,
            )
        except Exception as e:
            dbg = dict(getattr(state, "debug", {}) or {})
            dbg["retrieve_error"] = str(e)
            state.debug = dbg
            return state

    # 타이밍 기록
    timings = dict(getattr(state, "timings", {}) or {})
    timings["retrieve_ms"] = t.ms
    state.timings = timings

    # hits(dict) → Doc
    docs: list[Doc] = []
    for h in hits:
        meta = h.get("meta", {}) or {}
        title = h.get("title") or meta.get("invention_title") or ""
        text = meta.get("text") or meta.get("abstract") or meta.get("claims") or ""
        docs.append(Doc(
            id=str(h.get("id")),
            title=title,
            text=text,
            score=float(h.get("score", 0.0)),
            snippet=h.get("snippet"),
            meta=meta,
        ))

    state.docs = docs

    # 컨텍스트 문자열 생성(Answer 노드가 state.ctx 우선 사용)
    top_n = _to_int(extra.get("ctx_top_n")) or 6
    state.ctx = _build_ctx_from_docs(docs[:top_n])

    # 디버그 요약
    dbg = dict(getattr(state, "debug", {}) or {})
    dbg["retrieve"] = {
        "collections": getattr(_qds, "collections", None) or [getattr(_qds, "collection", "unknown")],
        "limit": limit,
        "k_each": k_each,
        "interleave": interleave,
        "total_hits": len(docs),
        "filter_keys": [k for k in extra.keys() if k.endswith("_gte") or k.endswith("_lte") or k.startswith("ipc_")],
        "top": [
            {
                "collection": h.get("collection"),
                "id": str(h.get("id")),
                "score": float(h.get("score", 0.0)),
                "title": (h.get("title") or "")[:120],
                "documentId": (h.get("meta", {}).get("documentId")),
            }
            for h in hits[:10]
        ],
    }
    state.debug = dbg

    return state

# ctdmate/rag/indexer.py
from __future__ import annotations
import os, json, uuid, hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterable

# --- config / deps ---
try:
    from ctdmate.app import config as CFG
except Exception:
    from ..app import config as CFG  # type: ignore

try:
    from qdrant_client import QdrantClient, models
except Exception as e:
    raise RuntimeError("qdrant-client가 필요합니다. pip install qdrant-client") from e

try:
    from fastembed import TextEmbedding
except Exception as e:
    raise RuntimeError("FastEmbed가 필요합니다. pip install fastembed") from e

# 선택: 파서 호출( --parse 옵션)
def _maybe_parse_to_jsonl(inputs: List[str]) -> List[str]:
    jsonls: List[str] = []
    from ctdmate.tools.smartdoc_upstage import run as parse_run  # 늦은 임포트
    outs = parse_run(inputs)
    for r in outs.get("results", []):
        j = r.get("rag_jsonl")
        if j:
            jsonls.append(j)
    return jsonls

# ---- 유틸 ----
E5_DOC_PREFIX = os.getenv("E5_DOC_PREFIX", "passage: ")

def _sha256(s: str | bytes) -> str:
    h = hashlib.sha256()
    h.update(s if isinstance(s, bytes) else s.encode("utf-8"))
    return h.hexdigest()

def _norm_text(s: str) -> str:
    return " ".join((s or "").split())

def _as_list(x: Any) -> List[Any]:
    if x is None: return []
    if isinstance(x, list): return x
    return [x]

def _probe_dim(embedder: TextEmbedding) -> int:
    v = embedder.embed(["dimension probe"])[0]
    return len(v)

# ---- 인덱서 본체 ----
class Indexer:
    """
    JSONL(chunk) → Qdrant 업서트.
    - 입력: {"id"?, "text", "metadata": {...}} 라인별 JSON
    - 벡터: FastEmbed(E5 호환), cosine
    - 중복: id가 없으면 sha256(source+text) 16자리로 생성 → 동일 id면 upsert 덮어쓰기
    """
    def __init__(
        self,
        collection: Optional[str] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        recreate: bool = False,
        batch_size: int = 128,
    ):
        self.collection = collection or CFG.QDRANT_GUIDE_COLLECTION
        self.client = QdrantClient(url=url or CFG.QDRANT_URL, api_key=api_key or CFG.QDRANT_API_KEY, prefer_grpc=False)
        self.embedder = TextEmbedding(model_name=CFG.EMBED_MODEL)
        self.dim = _probe_dim(self.embedder)
        self.batch_size = int(batch_size)
        self._ensure_collection(recreate=recreate)

    # ---- 컬렉션 보장 ----
    def _ensure_collection(self, recreate: bool = False):
        exists = False
        try:
            info = self.client.get_collection(self.collection)
            exists = bool(info)
        except Exception:
            exists = False
        if exists and recreate:
            self.client.delete_collection(self.collection); exists = False
        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=self.dim, distance=models.Distance.COSINE),
                optimizers_config=models.OptimizersConfigDiff(indexing_threshold=20000),
            )

    # ---- 임베딩 ----
    def _embed(self, texts: List[str]) -> List[List[float]]:
        docs = [E5_DOC_PREFIX + _norm_text(t) for t in texts]
        return list(self.embedder.embed(docs))  # generator → list

    # ---- 업서트 ----
    def _to_point(self, pid: str, vec: List[float], payload: Dict[str, Any]) -> models.PointStruct:
        return models.PointStruct(id=pid, vector=vec, payload=payload)

    def upsert_points(self, points: List[models.PointStruct]) -> None:
        if not points: return
        self.client.upsert(collection_name=self.collection, points=points)

    # ---- JSONL 파서 ----
    def _iter_jsonl(self, path: Path) -> Iterable[Dict[str, Any]]:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and obj.get("text"):
                        yield obj
                except Exception:
                    continue

    def _payload_from_obj(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        md = obj.get("metadata") or {}
        # 상위 호환: module/section/region/title/keywords도 허용
        payload = {
            "text": obj.get("text", ""),
            "source": md.get("source") or obj.get("source"),
            "file_name": md.get("file_name") or obj.get("file_name"),
            "page": md.get("page"),
            "sheet_name": md.get("sheet_name"),
            "heading": md.get("heading"),
            "heading_level": md.get("heading_level"),
            "module": md.get("module") or obj.get("module") or "GENERAL",
            "section": md.get("section") or obj.get("section"),
            "region": md.get("region") or obj.get("region") or "ICH-global",
            "title": md.get("title") or obj.get("title"),
            "keywords": md.get("keywords") or obj.get("keywords"),
            "created_at": md.get("created_at"),
            "char_len": md.get("char_len"),
            "approx_tokens": md.get("approx_tokens"),
        }
        # 해시(중복 관리 및 필터)
        payload["content_hash"] = _sha256((payload.get("source") or "") + "\n" + payload["text"])[:32]
        return payload

    def _point_id(self, obj: Dict[str, Any], payload: Dict[str, Any]) -> str:
        if obj.get("id"):
            return str(obj["id"])
        # 안정적 id: source+hash 기반
        base = (payload.get("source") or "") + payload.get("content_hash", _sha256(payload["text"]))
        return _sha256(base)[:16]

    # ---- JSONL 인덱싱 ----
    def index_jsonl(self, jsonl_path: str) -> Dict[str, Any]:
        p = Path(jsonl_path)
        if not p.exists():
            return {"ok": False, "file": str(p), "error": "not_found"}
        points: List[models.PointStruct] = []
        texts: List[str] = []
        metas: List[Dict[str, Any]] = []
        ids: List[str] = []

        for obj in self._iter_jsonl(p):
            payload = self._payload_from_obj(obj)
            pid = self._point_id(obj, payload)
            ids.append(pid); metas.append(payload); texts.append(payload["text"])

            if len(texts) >= self.batch_size:
                vecs = self._embed(texts)
                pts = [self._to_point(pid, v, pl) for pid, v, pl in zip(ids, vecs, metas)]
                self.upsert_points(pts)
                points.extend(pts)
                texts.clear(); metas.clear(); ids.clear()

        if texts:
            vecs = self._embed(texts)
            pts = [self._to_point(pid, v, pl) for pid, v, pl in zip(ids, vecs, metas)]
            self.upsert_points(pts)
            points.extend(pts)

        return {"ok": True, "file": str(p), "upserted": len(points), "collection": self.collection}

    # ---- 디렉토리 일괄 ----
    def index_dir(self, dir_path: str, pattern: str = "*.jsonl") -> Dict[str, Any]:
        d = Path(dir_path)
        files = sorted(list(d.rglob(pattern)))
        total = 0; items = []
        for f in files:
            res = self.index_jsonl(str(f))
            total += int(res.get("upserted", 0))
            items.append(res)
        return {"ok": True, "total_upserted": total, "files": len(files), "details": items}

# ---- CLI ----
def _expand_inputs(paths: List[str]) -> List[str]:
    outs: List[str] = []
    for p in paths:
        P = Path(p)
        if P.is_file():
            outs.append(str(P))
        elif P.is_dir():
            outs.extend([str(x) for x in P.rglob("*.jsonl")])
        else:
            # 글롭 문자열
            outs.extend([str(x) for x in Path(".").rglob(p)])
    return outs

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="RAG JSONL → Qdrant 인덱서")
    ap.add_argument("inputs", nargs="+", help="jsonl 파일/디렉토리/글롭. --parse 사용 시 pdf/xlsx도 허용")
    ap.add_argument("--collection", default=CFG.QDRANT_GUIDE_COLLECTION)
    ap.add_argument("--recreate", action="store_true", help="컬렉션 재생성")
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--parse", action="store_true", help="입력이 pdf/xlsx면 smartdoc_upstage로 JSONL 생성 후 인덱싱")
    args = ap.parse_args()

    # 입력 확장
    paths = _expand_inputs(args.inputs)

    # 선택 파싱
    jsonls: List[str] = []
    if args.parse:
        # pdf/xlsx만 걸러 파싱
        parse_targets = [p for p in paths if Path(p).suffix.lower() in {".pdf", ".xlsx"}]
        if parse_targets:
            jsonls.extend(_maybe_parse_to_jsonl(parse_targets))
        # 나머지 jsonl 포함
        jsonls.extend([p for p in paths if Path(p).suffix.lower() == ".jsonl"])
    else:
        jsonls = [p for p in paths if Path(p).suffix.lower() == ".jsonl"]

    if not jsonls:
        raise SystemExit("인덱싱할 JSONL이 없습니다. (--parse로 pdf/xlsx를 변환하거나 JSONL 경로를 지정)")

    ix = Indexer(collection=args.collection, recreate=args.recreate, batch_size=args.batch)
    total = 0
    details = []
    for j in jsonls:
        res = ix.index_jsonl(j)
        details.append(res); total += int(res.get("upserted", 0))

    print(json.dumps({"ok": True, "collection": args.collection, "indexed": total, "files": len(jsonls), "details": details}, ensure_ascii=False, indent=2))

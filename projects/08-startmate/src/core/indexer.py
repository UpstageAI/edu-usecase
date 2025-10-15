import json, uuid
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from .config import settings
from .embed_client import EmbeddingClient

class Indexer(BaseModel):
    client: QdrantClient | None = None
    emb: EmbeddingClient | None = None

    def __init__(self, **data):
        super().__init__(**data)
        self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_key)
        self.emb = EmbeddingClient()

    def ensure_collection(self, dim: int):
        try:
            self.client.get_collection(settings.qdrant_collection)
        except Exception:
            self.client.recreate_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
            )

    def upsert_jsonl(self, path: str, batch_size: int = 64):
        buf_texts: list[str] = []
        buf_payloads: list[dict] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                txt = item.get("text","").strip()
                if not txt:
                    continue
                buf_texts.append(txt)
                payload = {"text": txt}
                for k,v in item.items():
                    if k != "text":
                        payload[k] = v
                buf_payloads.append(payload)

                if len(buf_texts) >= batch_size:
                    self._flush(buf_texts, buf_payloads)
                    buf_texts, buf_payloads = [], []
        if buf_texts:
            self._flush(buf_texts, buf_payloads)

    def _flush(self, texts: list[str], payloads: list[dict]):
        vecs = self.emb.embed_batch(texts)
        dim = len(vecs[0]) if vecs else 0
        self.ensure_collection(dim)
        points = []
        for v, pl in zip(vecs, payloads):
            points.append(qm.PointStruct(id=str(uuid.uuid4()), vector=v, payload=pl))
        self.client.upsert(collection_name=settings.qdrant_collection, points=points)

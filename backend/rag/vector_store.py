import uuid
from functools import lru_cache
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (Distance, FieldCondition, Filter,
                                  MatchValue, PointStruct, VectorParams)

from backend.config import COLLECTION_NAME, EMBEDDING_DIMENSION, QDRANT_PATH


@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    client = QdrantClient(path=QDRANT_PATH)
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
        )
    return client


def _to_uuid(s: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))


def add_documents(
    ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
) -> None:
    points = [
        PointStruct(
            id=_to_uuid(id_),
            vector=emb,
            payload={**meta, "_document": doc},
        )
        for id_, emb, doc, meta in zip(ids, embeddings, documents, metadatas)
    ]
    _client().upsert(collection_name=COLLECTION_NAME, points=points)


def query_documents(
    query_embedding: List[float],
    n_results: int = 5,
    where: Optional[Dict] = None,
) -> Dict:
    q_filter = _build_filter(where) if where else None
    hits = _client().search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=n_results,
        query_filter=q_filter,
        with_payload=True,
    )
    docs, metas, distances = [], [], []
    for h in hits:
        payload = h.payload or {}
        docs.append(payload.get("_document", ""))
        metas.append({k: v for k, v in payload.items() if k != "_document"})
        distances.append(round(1 - h.score, 6))

    return {"documents": [docs], "metadatas": [metas], "distances": [distances]}


def collection_count() -> int:
    try:
        return _client().count(collection_name=COLLECTION_NAME).count
    except Exception:
        return 0


def get_all_by_type(doc_type: str) -> List[Dict[str, Any]]:
    """Return all payloads matching a doc_type — used for stats."""
    records, offset = [], None
    while True:
        batch, offset = _client().scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="doc_type", match=MatchValue(value=doc_type))]
            ),
            with_payload=True,
            with_vectors=False,
            limit=100,
            offset=offset,
        )
        records.extend(r.payload for r in batch if r.payload)
        if offset is None:
            break
    return records


def _build_filter(where: Dict) -> Filter:
    if "$and" in where:
        return Filter(must=[_parse_cond(c) for c in where["$and"]])
    return Filter(must=[_parse_cond(where)])


def _parse_cond(cond: Dict) -> FieldCondition:
    for field, op in cond.items():
        if isinstance(op, dict) and "$eq" in op:
            return FieldCondition(key=field, match=MatchValue(value=op["$eq"]))
    raise ValueError(f"Unsupported filter: {cond}")

from typing import Any, Dict, List, Optional

from backend.config import TOP_K_RETRIEVAL
from backend.rag.embedder import embed_query
from backend.rag.vector_store import query_documents


def build_where_filter(
    district: Optional[str] = None,
    year: Optional[int] = None,
    doc_type: Optional[str] = None,
) -> Optional[Dict]:
    conditions = []
    if district:
        conditions.append({"district": {"$eq": district}})
    if year:
        conditions.append({"year": {"$eq": year}})
    if doc_type:
        conditions.append({"doc_type": {"$eq": doc_type}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def retrieve(
    query: str,
    top_k: int = TOP_K_RETRIEVAL,
    district: Optional[str] = None,
    year: Optional[int] = None,
    doc_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    embedding = embed_query(query)
    where = build_where_filter(district, year, doc_type)
    results = query_documents(embedding, n_results=top_k, where=where)

    retrieved = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, distances):
        retrieved.append({
            "text": doc,
            "metadata": meta,
            "relevance_score": round(1 - dist, 4),
        })

    return retrieved


def format_context_for_llm(retrieved_docs: List[Dict[str, Any]]) -> str:
    if not retrieved_docs:
        return ""

    parts = []
    for i, item in enumerate(retrieved_docs, 1):
        meta = item["metadata"]
        source_line = f"[{i}] Source: {meta.get('source', 'Unknown')}"
        if meta.get("district"):
            source_line += f" | District: {meta['district']}"
        if meta.get("date"):
            source_line += f" | Date: {meta['date']}"
        if meta.get("doc_type"):
            source_line += f" | Type: {meta['doc_type']}"
        parts.append(f"{source_line}\n    {item['text']}")

    return "\n\n".join(parts)


def build_source_cards(retrieved_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cards = []
    for i, item in enumerate(retrieved_docs, 1):
        meta = item["metadata"]
        cards.append({
            "index": i,
            "source": meta.get("source", "Unknown"),
            "doc_type": meta.get("doc_type", ""),
            "district": meta.get("district", ""),
            "date": meta.get("date", ""),
            "year": meta.get("year", ""),
            "incident_type": meta.get("incident_type", ""),
            "title": meta.get("title", ""),
            "relevance": item["relevance_score"],
            "excerpt": item["text"][:220] + "..." if len(item["text"]) > 220 else item["text"],
        })
    return cards

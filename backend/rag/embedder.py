import httpx

from backend.config import EMBEDDING_MODEL, OLLAMA_BASE_URL


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using nomic-embed-text via Ollama."""
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": texts},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]

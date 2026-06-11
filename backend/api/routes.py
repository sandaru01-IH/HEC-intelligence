import json
from typing import Optional

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import LLM_MODEL, OLLAMA_BASE_URL, SYSTEM_PROMPT
from backend.llm.ollama_provider import OllamaProvider
from backend.rag.retriever import build_source_cards, format_context_for_llm, retrieve
from backend.rag.vector_store import collection_count, get_all_by_type

router = APIRouter()
llm = OllamaProvider()


class ChatRequest(BaseModel):
    query: str
    district: Optional[str] = None
    year: Optional[int] = None
    doc_type: Optional[str] = None
    model: Optional[str] = None  # overrides default model per-request


class IngestRequest(BaseModel):
    force: bool = False


@router.get("/health")
async def health():
    llm_ok = await llm.health_check()
    docs = collection_count()
    return {
        "status": "ok" if llm_ok else "llm_unavailable",
        "model": llm.model_name(),
        "documents_indexed": docs,
        "llm_ready": llm_ok,
    }


@router.get("/models")
async def list_models():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
        return {"models": models, "default": LLM_MODEL}
    except Exception:
        return {"models": [LLM_MODEL], "default": LLM_MODEL}


@router.get("/stats")
async def stats():
    total = collection_count()
    inc_metas = get_all_by_type("incident")

    district_counts: dict = {}
    year_counts: dict = {}
    type_counts: dict = {}
    total_human_deaths = 0
    total_elephant_deaths = 0
    total_human_injuries = 0

    for m in inc_metas:
        d = m.get("district", "Unknown")
        district_counts[d] = district_counts.get(d, 0) + 1
        y = m.get("year", 0)
        if y:
            year_counts[str(y)] = year_counts.get(str(y), 0) + 1
        t = m.get("incident_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        total_human_deaths += m.get("human_deaths", 0)
        total_elephant_deaths += m.get("elephant_deaths", 0)
        total_human_injuries += m.get("human_injuries", 0)

    top_districts = sorted(district_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_documents": total,
        "total_incidents": len(inc_metas),
        "total_human_deaths": total_human_deaths,
        "total_human_injuries": total_human_injuries,
        "total_elephant_deaths": total_elephant_deaths,
        "top_districts": [{"district": d, "count": c} for d, c in top_districts],
        "by_year": dict(sorted(year_counts.items())),
        "by_type": type_counts,
    }


@router.get("/districts")
async def districts():
    metas = get_all_by_type("incident")
    seen = sorted(set(m.get("district", "") for m in metas if m.get("district")))
    return {"districts": seen}


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:  # 20 MB limit
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 20 MB.")

    from backend.ingestion.ingest import ingest_pdf
    result = ingest_pdf(file.filename, contents)

    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Failed to process PDF."))

    return result


@router.post("/chat")
async def chat(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    retrieved_docs = retrieve(
        query=req.query,
        district=req.district or None,
        year=req.year or None,
        doc_type=req.doc_type or None,
    )
    context = format_context_for_llm(retrieved_docs)
    source_cards = build_source_cards(retrieved_docs)

    async def event_stream():
        yield f"data: {json.dumps({'type': 'status', 'message': 'Searching knowledge base...'})}\n\n"

        if not retrieved_docs:
            yield f"data: {json.dumps({'type': 'status', 'message': 'No matching records — answering from domain knowledge...'})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'status', 'message': f'Found {len(retrieved_docs)} relevant records. Generating response...'})}\n\n"

        try:
            async for token in llm.stream(req.query, context, SYSTEM_PROMPT, model_override=req.model):
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'sources', 'sources': source_cards})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/ingest")
async def ingest(req: IngestRequest):
    from backend.ingestion.ingest import run_ingestion
    count = run_ingestion(force=req.force)
    return {"documents_indexed": count}


@router.post("/scan-kb")
async def scan_kb():
    """Re-scan the knowledge_base/ folder for new or changed PDFs."""
    from backend.ingestion.ingest import scan_knowledge_base
    result = scan_knowledge_base()
    total = collection_count()
    return {**result, "total_documents": total}

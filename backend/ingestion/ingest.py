import io
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backend.config import (DATA_DIR, DUMMY_DATA_DIR, PDF_CHUNK_OVERLAP,
                            PDF_CHUNK_SIZE, RAW_DATA_DIR)

KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
KB_MANIFEST_PATH   = KNOWLEDGE_BASE_DIR / ".manifest.json"
from backend.rag.embedder import embed_texts
from backend.rag.vector_store import add_documents, collection_count


# ── Dummy JSON loaders ────────────────────────────────────────

def _incident_to_text(inc: Dict[str, Any]) -> str:
    casualties = []
    hc = inc.get("human_casualties", {})
    ec = inc.get("elephant_casualties", {})
    if hc.get("deaths"):
        casualties.append(f"{hc['deaths']} human death(s)")
    if hc.get("injuries"):
        casualties.append(f"{hc['injuries']} human injury/injuries")
    if ec.get("deaths"):
        casualties.append(f"{ec['deaths']} elephant death(s)")
    casualty_str = "; ".join(casualties) if casualties else "no casualties"
    crops = ", ".join(inc.get("crops_damaged", [])) or "none"
    return (
        f"Incident ID: {inc['id']}. "
        f"Date: {inc['date']}. "
        f"District: {inc['district']}, Location: {inc['location']}. "
        f"Type: {inc['incident_type'].replace('_', ' ')}. "
        f"Elephants involved: {inc.get('elephants_involved', 'unknown')}. "
        f"Casualties: {casualty_str}. "
        f"Crops damaged: {crops}. "
        f"Area damaged: {inc.get('area_damaged_acres', 0)} acres. "
        f"Property damage: LKR {inc.get('property_damage_lkr', 0):,}. "
        f"Source: {inc['source']}. "
        f"Details: {inc['description']}"
    )


def _incident_to_metadata(inc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "doc_type": "incident",
        "id": inc["id"],
        "date": inc.get("date", ""),
        "year": inc.get("year", 0),
        "district": inc.get("district", ""),
        "location": inc.get("location", ""),
        "incident_type": inc.get("incident_type", ""),
        "source": inc.get("source", ""),
        "source_type": inc.get("source_type", ""),
        "nearby_park": inc.get("nearby_park", ""),
        "human_deaths": inc.get("human_casualties", {}).get("deaths", 0),
        "human_injuries": inc.get("human_casualties", {}).get("injuries", 0),
        "elephant_deaths": inc.get("elephant_casualties", {}).get("deaths", 0),
        "title": f"{inc.get('incident_type','').replace('_',' ').title()} — {inc.get('district','')} ({inc.get('date','')})",
    }


def _research_to_text(res: Dict[str, Any]) -> str:
    findings = " ".join(f"({i+1}) {f}" for i, f in enumerate(res.get("key_findings", [])))
    return (
        f"Research: {res['title']}. "
        f"Authors: {', '.join(res.get('authors', []))}. "
        f"Year: {res['year']}. "
        f"Journal: {res.get('journal', '')}. "
        f"Districts covered: {', '.join(res.get('districts_covered', []))}. "
        f"Abstract: {res['abstract']} "
        f"Key findings: {findings}"
    )


def _research_to_metadata(res: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "doc_type": "research",
        "id": res["id"],
        "title": res["title"],
        "year": res.get("year", 0),
        "journal": res.get("journal", ""),
        "district": res.get("districts_covered", [""])[0],
        "source": f"{', '.join(res.get('authors', []))} ({res.get('year', '')})",
        "date": str(res.get("year", "")),
        "incident_type": "",
        "source_type": "research_paper",
        "nearby_park": "",
        "human_deaths": 0,
        "human_injuries": 0,
        "elephant_deaths": 0,
        "location": "",
    }


def _prevention_to_text(prev: Dict[str, Any]) -> str:
    limitations = "; ".join(prev.get("limitations", []))
    suitable = ", ".join(prev.get("suitable_for", []))
    districts = ", ".join(prev.get("districts_recommended", []))
    return (
        f"Prevention method: {prev['method']}. "
        f"Category: {prev['category'].replace('_', ' ')}. "
        f"Effectiveness: {prev['effectiveness_rating']}. "
        f"Effectiveness notes: {prev['effectiveness_notes']} "
        f"Cost: {prev.get('cost_estimate', 'varies')}. "
        f"Suitable for: {suitable}. "
        f"Limitations: {limitations}. "
        f"Districts recommended: {districts}. "
        f"Implementation: {prev['implementation_notes']}"
    )


def _prevention_to_metadata(prev: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "doc_type": "prevention",
        "id": prev["id"],
        "title": prev["method"],
        "category": prev.get("category", ""),
        "effectiveness": prev.get("effectiveness_rating", ""),
        "district": prev.get("districts_recommended", [""])[0],
        "source": f"HEC Prevention Guidelines — {prev['method']}",
        "date": "",
        "year": 0,
        "incident_type": "",
        "source_type": "guideline",
        "nearby_park": "",
        "human_deaths": 0,
        "human_injuries": 0,
        "elephant_deaths": 0,
        "location": "",
    }


def load_dummy_data() -> Tuple[List[str], List[List[float]], List[str], List[Dict]]:
    all_ids, all_texts, all_metas = [], [], []

    for fname, to_text, to_meta in [
        ("incidents.json", _incident_to_text, _incident_to_metadata),
        ("research.json", _research_to_text, _research_to_metadata),
        ("prevention_guidelines.json", _prevention_to_text, _prevention_to_metadata),
    ]:
        fpath = DUMMY_DATA_DIR / fname
        if not fpath.exists():
            print(f"  [skip] {fname} not found")
            continue
        records = json.loads(fpath.read_text(encoding="utf-8"))
        for rec in records:
            all_ids.append(rec["id"])
            all_texts.append(to_text(rec))
            all_metas.append(to_meta(rec))
        print(f"  [loaded] {fname} — {len(records)} records")

    print(f"Embedding {len(all_texts)} documents...")
    embeddings = embed_texts(all_texts)
    return all_ids, embeddings, all_texts, all_metas


def run_ingestion(force: bool = False) -> int:
    existing = collection_count()
    if existing > 0 and not force:
        print(f"Collection already has {existing} dummy documents.")
    else:
        ids, embeddings, texts, metas = load_dummy_data()
        if ids:
            add_documents(ids, embeddings, texts, metas)
            print(f"Dummy data ingested — {len(ids)} documents.")

    print("\nScanning knowledge_base/ folder...")
    kb = scan_knowledge_base()
    if kb["new_chunks"]:
        print(f"Knowledge base: {kb['new_chunks']} new chunks from {kb['scanned']} PDFs.")

    total = collection_count()
    print(f"\nTotal documents in vector store: {total}")
    return total


# ── PDF ingestion ─────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = PDF_CHUNK_SIZE, overlap: int = PDF_CHUNK_OVERLAP) -> List[str]:
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def ingest_pdf(filename: str, file_bytes: bytes, prefix: str = "PDF") -> Dict[str, Any]:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("pypdf not installed. Run: pip install pypdf")

    reader = PdfReader(io.BytesIO(file_bytes))
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if not full_text:
        return {"success": False, "error": "No extractable text found in PDF."}

    chunks = _chunk_text(full_text)
    if not chunks:
        return {"success": False, "error": "PDF produced no usable text chunks."}

    upload_id = str(uuid.uuid4())[:8]
    source_type = "knowledge_base" if prefix == "KB" else "user_upload"
    ids, texts, metas = [], [], []

    for i, chunk in enumerate(chunks):
        chunk_id = f"{prefix}-{upload_id}-chunk-{i}"
        ids.append(chunk_id)
        texts.append(chunk)
        metas.append({
            "doc_type": "uploaded_pdf",
            "id": chunk_id,
            "title": filename,
            "source": filename,
            "upload_id": upload_id,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "date": "",
            "year": 0,
            "district": "",
            "location": "",
            "incident_type": "",
            "source_type": source_type,
            "nearby_park": "",
            "human_deaths": 0,
            "human_injuries": 0,
            "elephant_deaths": 0,
        })

    embeddings = embed_texts(texts)
    add_documents(ids, embeddings, texts, metas)

    return {
        "success": True,
        "upload_id": upload_id,
        "filename": filename,
        "pages": len(reader.pages),
        "chunks_added": len(chunks),
    }


# ── Knowledge base folder scanning ───────────────────────────

def _load_manifest() -> Dict[str, Any]:
    try:
        if KB_MANIFEST_PATH.exists():
            return json.loads(KB_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_manifest(manifest: Dict[str, Any]) -> None:
    KB_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def scan_knowledge_base() -> Dict[str, Any]:
    """Scan data/knowledge_base/ and ingest any new or changed PDFs."""
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()
    pdfs = sorted(KNOWLEDGE_BASE_DIR.glob("*.pdf"))

    if not pdfs:
        print("  [kb] No PDFs found in knowledge_base/ folder.")
        return {"scanned": 0, "new_chunks": 0}

    new_chunks = 0
    for pdf in pdfs:
        stat = pdf.stat()
        cached = manifest.get(pdf.name, {})
        # Skip if file hasn't changed (same size + mtime within 1s)
        if (cached.get("size") == stat.st_size and
                abs(cached.get("mtime", 0) - stat.st_mtime) < 1.0):
            print(f"  [kb] Already indexed: {pdf.name}")
            continue

        print(f"  [kb] Ingesting: {pdf.name}")
        result = ingest_pdf(pdf.name, pdf.read_bytes(), prefix="KB")
        if result.get("success"):
            manifest[pdf.name] = {
                "upload_id": result["upload_id"],
                "chunks": result["chunks_added"],
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            }
            new_chunks += result["chunks_added"]
            print(f"  [kb] Done: {result['chunks_added']} chunks from {pdf.name}")
        else:
            print(f"  [kb] Failed: {result.get('error')}")

    _save_manifest(manifest)
    return {"scanned": len(pdfs), "new_chunks": new_chunks}

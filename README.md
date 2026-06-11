# HEC Intelligence

> An AI-powered intelligence platform for querying Human-Elephant Conflict (HEC) incident data, research findings, and prevention strategies across Sri Lanka — through natural language.

**Team MetroMinds** · Department of Town and Country Planning · University of Moratuwa · 2026

---

## Overview

HEC Intelligence is a full-stack AI system that enables communities, field officers, and researchers to explore Sri Lanka's human-elephant conflict landscape through conversational queries. It combines a fine-tunable LLM with Retrieval-Augmented Generation (RAG) over a structured knowledge base of incidents, research papers, and prevention guidelines — and supports user-uploaded PDFs for session-specific context.

---

## Features

- **Natural language querying** — ask anything about HEC incidents, affected districts, research findings, or prevention strategies
- **RAG pipeline** — hybrid retrieval over structured dummy/real data and user-uploaded PDFs using Qdrant vector search
- **Streaming responses** — Server-Sent Events (SSE) for real-time token streaming
- **PDF ingestion** — upload your own documents; they are chunked, embedded, and queried alongside the core knowledge base
- **Permanent knowledge base** — drop PDFs into `data/knowledge_base/` for persistent indexing across sessions
- **Model-agnostic LLM** — swap models via `.env` or the in-app model picker (Ollama-served models)
- **Filters** — narrow results by district, year, or document type before querying
- **Bubble chat UI** — clean left/right message layout with copy, view-sources, and regenerate actions per response
- **Sources panel** — slide-in right panel showing retrieved context cards per response
- **Dark / light theme** — persistent across sessions
- **Out-of-domain handling** — gracefully redirects non-HEC queries

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Frontend (Vanilla JS)           │
│   Bubble chat UI · Filters · PDF upload · SSE   │
└──────────────────────┬──────────────────────────┘
                       │ HTTP / SSE
┌──────────────────────▼──────────────────────────┐
│              FastAPI Backend                     │
│  /api/chat  /api/upload  /api/stats  /api/scan-kb│
└──────┬───────────────────────────┬──────────────┘
       │                           │
┌──────▼──────┐           ┌────────▼────────┐
│   Qdrant    │           │  Ollama (local) │
│ Vector Store│           │  LLM + Embedder │
│  (RAG)      │           │  gemma3:4b +    │
└─────────────┘           │  nomic-embed-text│
                          └─────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla JS, CSS custom properties |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| LLM Inference | Ollama (model-agnostic) |
| Embeddings | `nomic-embed-text` via Ollama `/api/embed` |
| Vector Store | Qdrant (local persistent client) |
| PDF Parsing | pypdf |
| Fine-tuning scaffold | LoRA / QLoRA (Phase 3) |

---

## Getting Started

### Prerequisites

- [Python 3.11+](https://www.python.org/)
- [Ollama](https://ollama.com/) installed and running locally
- Required Ollama models pulled:

```bash
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/sandaru01-IH/HEC-intelligence.git
cd HEC-intelligence

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env if you want to change the default model

# 5. Ingest the knowledge base
python scripts/run_ingest.py

# 6. Start the server
uvicorn backend.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Usage

### Querying
Type any natural language question into the chat input. Example queries:

- *"Which districts in Sri Lanka have the highest number of HEC incidents?"*
- *"What are the most effective elephant deterrent methods?"*
- *"How many human fatalities were recorded near Minneriya National Park?"*
- *"What does research say about electric fence effectiveness?"*

### Uploading PDFs
Click the **paperclip icon** in the input bar to upload PDF documents. They are chunked and embedded automatically and become part of the retrieval context for your session.

### Permanent Knowledge Base
Drop PDF files into `data/knowledge_base/`. Trigger re-indexing via the `/api/scan-kb` endpoint or by restarting the server with ingestion enabled.

### Switching Models
Use the **Model** picker in the sidebar to switch between any Ollama-served model at runtime.

---

## Project Structure

```
hec-intelligence/
├── backend/
│   ├── api/
│   │   └── routes.py          # FastAPI route handlers
│   ├── ingestion/
│   │   └── ingest.py          # PDF & dummy data ingestion
│   ├── llm/
│   │   ├── base.py            # LLM provider interface
│   │   └── ollama_provider.py # Ollama streaming implementation
│   ├── rag/
│   │   ├── embedder.py        # nomic-embed-text via Ollama
│   │   ├── retriever.py       # Hybrid retrieval + source cards
│   │   └── vector_store.py    # Qdrant client wrapper
│   ├── config.py              # Central configuration
│   └── main.py                # FastAPI app entry point
├── data/
│   ├── dummy/                 # Seed knowledge base (JSON)
│   │   ├── incidents.json
│   │   ├── research.json
│   │   └── prevention_guidelines.json
│   ├── knowledge_base/        # Drop PDFs here for permanent indexing
│   └── raw/                   # Raw data staging (optional)
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── scripts/
│   ├── run_ingest.py          # CLI ingestion tool (--force flag)
│   ├── fine_tune.py           # LoRA/QLoRA fine-tuning scaffold
│   └── evaluate.py            # BLEU / ROUGE / METEOR evaluation
├── .env.example
├── requirements.txt
└── README.md
```

---

## Data

The system ships with structured seed data in `data/dummy/`:

| Dataset | Records | Description |
|---|---|---|
| `incidents.json` | 25 | HEC incidents 2019–2024 across 10 districts |
| `research.json` | 8 | Peer-reviewed research papers |
| `prevention_guidelines.json` | 12 | Prevention and mitigation strategies |

Real incident data can be ingested by replacing or extending these files and running `python scripts/run_ingest.py --force`.

---

## Roadmap

- [x] RAG pipeline with Qdrant + nomic-embed-text
- [x] Streaming LLM responses (SSE)
- [x] PDF upload and knowledge base ingestion
- [x] Bubble chat UI with action icons
- [x] Sources side panel
- [x] Dark / light theme
- [ ] Real incident dataset integration
- [ ] LoRA fine-tuning on domain-specific corpus
- [ ] BLEU / ROUGE evaluation pipeline
- [ ] Deployment packaging

---

## Team

**Team MetroMinds**
Department of Town and Country Planning
Faculty of Architecture, University of Moratuwa · Sri Lanka · 2026

---

## License

This project was developed as an academic research prototype. All rights reserved by Team MetroMinds, University of Moratuwa.

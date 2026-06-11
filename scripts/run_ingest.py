"""Run this once (or with --force) to load data into the ChromaDB vector store."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.ingestion.ingest import run_ingestion

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest HEC data into ChromaDB")
    parser.add_argument("--force", action="store_true", help="Re-ingest even if documents exist")
    args = parser.parse_args()

    print("=== HEC Intelligence System — Data Ingestion ===")
    count = run_ingestion(force=args.force)
    print(f"Done. {count} documents available for retrieval.")

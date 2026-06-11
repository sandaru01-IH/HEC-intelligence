"""
Phase 4 Evaluation — BLEU, ROUGE, METEOR scoring for HEC model responses.

Usage:
  python scripts/evaluate.py --predictions predictions.jsonl --references references.jsonl

Both files must be newline-delimited JSON, one object per line:
  {"id": "q1", "text": "..."}
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

import nltk
from nltk.translate.bleu_score import SmoothingFunction, corpus_bleu
from nltk.translate.meteor_score import meteor_score
from rouge_score import rouge_scorer

nltk.download("wordnet", quiet=True)
nltk.download("punkt", quiet=True)
nltk.download("omw-1.4", quiet=True)


def load_jsonl(path: str) -> List[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def compute_bleu(predictions: List[str], references: List[str]) -> float:
    tokenized_preds = [nltk.word_tokenize(p.lower()) for p in predictions]
    tokenized_refs  = [[nltk.word_tokenize(r.lower())] for r in references]
    sf = SmoothingFunction().method1
    return round(corpus_bleu(tokenized_refs, tokenized_preds, smoothing_function=sf), 4)


def compute_rouge(predictions: List[str], references: List[str]) -> dict:
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    r1, r2, rl = [], [], []
    for pred, ref in zip(predictions, references):
        s = scorer.score(ref, pred)
        r1.append(s["rouge1"].fmeasure)
        r2.append(s["rouge2"].fmeasure)
        rl.append(s["rougeL"].fmeasure)
    return {
        "rouge1": round(sum(r1) / len(r1), 4),
        "rouge2": round(sum(r2) / len(r2), 4),
        "rougeL": round(sum(rl) / len(rl), 4),
    }


def compute_meteor(predictions: List[str], references: List[str]) -> float:
    scores = []
    for pred, ref in zip(predictions, references):
        tok_pred = nltk.word_tokenize(pred.lower())
        tok_ref  = nltk.word_tokenize(ref.lower())
        scores.append(meteor_score([tok_ref], tok_pred))
    return round(sum(scores) / len(scores), 4)


def run_evaluation(pred_path: str, ref_path: str) -> None:
    preds_raw = load_jsonl(pred_path)
    refs_raw  = load_jsonl(ref_path)

    pred_map = {r["id"]: r["text"] for r in preds_raw}
    ref_map  = {r["id"]: r["text"] for r in refs_raw}

    shared_ids = sorted(set(pred_map) & set(ref_map))
    if not shared_ids:
        print("ERROR: No matching IDs found between prediction and reference files.")
        sys.exit(1)

    predictions = [pred_map[i] for i in shared_ids]
    references  = [ref_map[i]  for i in shared_ids]

    print(f"\n=== HEC Evaluation Results ({len(shared_ids)} samples) ===\n")

    bleu   = compute_bleu(predictions, references)
    rouge  = compute_rouge(predictions, references)
    meteor = compute_meteor(predictions, references)

    print(f"  BLEU      : {bleu:.4f}")
    print(f"  ROUGE-1   : {rouge['rouge1']:.4f}")
    print(f"  ROUGE-2   : {rouge['rouge2']:.4f}")
    print(f"  ROUGE-L   : {rouge['rougeL']:.4f}")
    print(f"  METEOR    : {meteor:.4f}")
    print()

    out = {
        "n_samples": len(shared_ids),
        "bleu": bleu,
        "rouge1": rouge["rouge1"],
        "rouge2": rouge["rouge2"],
        "rougeL": rouge["rougeL"],
        "meteor": meteor,
    }
    out_path = Path(pred_path).parent / "eval_results.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Results saved to: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate HEC model responses")
    parser.add_argument("--predictions", required=True, help="Path to predictions JSONL file")
    parser.add_argument("--references",  required=True, help="Path to reference answers JSONL file")
    args = parser.parse_args()
    run_evaluation(args.predictions, args.references)

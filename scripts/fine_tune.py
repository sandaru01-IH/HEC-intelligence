"""
Phase 3 — LoRA/QLoRA Fine-Tuning Scaffold for HEC domain.

Prerequisites (install separately when ready for Phase 3):
  pip install transformers peft datasets accelerate bitsandbytes trl

Usage:
  python scripts/fine_tune.py --model meta-llama/Llama-3.2-3B-Instruct --data data/finetune/hec_qa.jsonl

Training data format (JSONL, one sample per line):
  {"instruction": "What happened in Minneriya in 2023?", "response": "In 2023, there were multiple elephant raids..."}
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_training_data(path: str):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def format_sample(sample: dict) -> str:
    instruction = sample.get("instruction", "")
    response    = sample.get("response", "")
    context     = sample.get("context", "")

    if context:
        return (
            f"<|system|>You are an expert on Human-Elephant Conflict in Sri Lanka.<|end|>\n"
            f"<|user|>Context: {context}\n\nQuestion: {instruction}<|end|>\n"
            f"<|assistant|>{response}<|end|>"
        )
    return (
        f"<|system|>You are an expert on Human-Elephant Conflict in Sri Lanka.<|end|>\n"
        f"<|user|>{instruction}<|end|>\n"
        f"<|assistant|>{response}<|end|>"
    )


def run_fine_tuning(model_name: str, data_path: str, output_dir: str, epochs: int = 3) -> None:
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import (AutoModelForCausalLM, AutoTokenizer,
                                  BitsAndBytesConfig, TrainingArguments)
        from trl import SFTTrainer
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install with: pip install transformers peft datasets accelerate bitsandbytes trl")
        sys.exit(1)

    import torch

    print(f"Loading base model: {model_name}")
    print(f"Training data: {data_path}")
    print(f"Output: {output_dir}")

    records = load_training_data(data_path)
    texts = [format_sample(r) for r in records]
    dataset = Dataset.from_dict({"text": texts})
    print(f"Training samples: {len(texts)}")

    use_4bit = torch.cuda.is_available()
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=use_4bit,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    ) if use_4bit else None

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        optim="paged_adamw_32bit",
        save_strategy="epoch",
        logging_steps=10,
        learning_rate=2e-4,
        fp16=use_4bit,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("\nStarting fine-tuning...")
    trainer.train()

    adapter_path = Path(output_dir) / "hec_lora_adapter"
    model.save_pretrained(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))
    print(f"\nFine-tuned adapter saved to: {adapter_path}")
    print("To use: load the base model + this adapter with PEFT, or export to GGUF for Ollama.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune LLM on HEC data with LoRA/QLoRA")
    parser.add_argument("--model",      default="microsoft/Phi-3.5-mini-instruct",
                        help="HuggingFace model ID or local path")
    parser.add_argument("--data",       required=True, help="Path to training JSONL file")
    parser.add_argument("--output",     default="models/hec_finetuned", help="Output directory")
    parser.add_argument("--epochs",     type=int, default=3, help="Number of training epochs")
    args = parser.parse_args()

    run_fine_tuning(args.model, args.data, args.output, args.epochs)

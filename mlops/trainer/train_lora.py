"""QLoRA fine-tuning entrypoint, packaged and submitted by ../train.py as a
Vertex AI CustomJob. Runs INSIDE that job's container, on the GPU Vertex AI
attaches -- never run directly on a laptop (no GPU here fits Gemma 4 E4B, see
docs/architecture.md).

UNVERIFIED: written against the current transformers/peft/bitsandbytes APIs
from documentation, not run against a real GPU (none available in this
environment that fits the model). Treat this as a solid starting point to
smoke-test on a real L4/T4, not as validated code -- the orchestration in
train.py (job submission, Experiments logging, adapter upload) is the part
that's actually exercised by this setup.
"""

from __future__ import annotations

import argparse
import json

import google.cloud.aiplatform as aiplatform
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--train-file", required=True, help="gs:// path to train.jsonl")
    p.add_argument("--eval-file", required=True, help="gs:// path to eval.jsonl")
    p.add_argument("--output-dir", required=True, help="gs:// path to write the LoRA adapter")
    p.add_argument("--base-model", default="google/gemma-4-e4b")
    p.add_argument("--experiment", required=True)
    p.add_argument("--run-name", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--location", default="us-central1")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    aiplatform.init(project=args.project, location=args.location, experiment=args.experiment)
    aiplatform.start_run(args.run_name)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True),
        device_map="auto",
    )
    model = get_peft_model(
        model,
        LoraConfig(r=32, lora_alpha=64, lora_dropout=0.05, task_type="CAUSAL_LM"),
    )

    def _format(example: dict) -> dict:
        text = tokenizer.apply_chat_template(example["messages"], tokenize=False)
        return tokenizer(text, truncation=True, max_length=2048)

    train_ds = load_dataset("json", data_files=args.train_file, split="train").map(_format)
    eval_ds = load_dataset("json", data_files=args.eval_file, split="train").map(_format)

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir="/tmp/decision-lora",
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            num_train_epochs=2,
            learning_rate=2e-4,
            logging_steps=10,
            eval_strategy="epoch",
            save_strategy="epoch",
            report_to=[],
        ),
        train_dataset=train_ds,
        eval_dataset=eval_ds,
    )
    trainer.train()
    metrics = trainer.evaluate()
    aiplatform.log_metrics(metrics)
    print(json.dumps(metrics))

    model.save_pretrained("/tmp/decision-lora/adapter")
    tokenizer.save_pretrained("/tmp/decision-lora/adapter")

    from google.cloud import storage

    bucket_name, prefix = args.output_dir.removeprefix("gs://").split("/", 1)
    bucket = storage.Client(project=args.project).bucket(bucket_name)
    import pathlib

    for path in pathlib.Path("/tmp/decision-lora/adapter").rglob("*"):
        if path.is_file():
            blob_name = f"{prefix}/{path.relative_to('/tmp/decision-lora/adapter')}"
            bucket.blob(blob_name).upload_from_filename(str(path))

    aiplatform.end_run()


if __name__ == "__main__":
    main()

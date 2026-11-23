"""Step 3 (docs/architecture.md): score the new adapter against current
production and the zero-shot baseline, on held-out real orders (eval.jsonl
from prepare_data.py -- never seen during training).

Calls the live model-serving vLLM endpoint directly (same endpoint
hotswap.py targets) rather than re-implementing inference, so "did the
adapter actually help" is measured through the exact serving path production
traffic uses.
"""

from __future__ import annotations

import json
import os
import sys

import requests

MODEL_SERVING_URL = os.environ.get("MODEL_SERVING_URL", "http://model-serving.vertex-demo.svc.cluster.local:8000")


def _predict(model_name: str, messages: list[dict]) -> dict:
    resp = requests.post(
        f"{MODEL_SERVING_URL}/v1/chat/completions",
        json={"model": model_name, "messages": messages[:-1], "max_tokens": 200},
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def _score(model_name: str, eval_examples: list[dict]) -> dict:
    errors, correct = [], 0
    for ex in eval_examples:
        target = json.loads(ex["messages"][-1]["content"])
        try:
            pred = _predict(model_name, ex["messages"])
        except Exception as exc:  # noqa: BLE001 -- a bad eval example shouldn't kill the whole run
            print(f"skipping example, prediction failed: {exc}", file=sys.stderr)
            continue
        errors.append(abs(pred.get("keep_confidence_pct", 0) - target["keep_confidence_pct"]))
        correct += int(pred.get("risk_category") == target["risk_category"])

    n = max(len(errors), 1)
    return {
        "mean_abs_error_pct": sum(errors) / n,
        "risk_category_accuracy": correct / n,
        "n_examples": len(errors),
    }


def main() -> None:
    eval_path = sys.argv[1] if len(sys.argv) > 1 else "mlops/_data/eval.jsonl"
    examples = [json.loads(line) for line in open(eval_path) if line.strip()]

    candidate_name = sys.argv[2] if len(sys.argv) > 2 else "gemma-4-e4b-decision-candidate"

    results = {
        "candidate": _score(candidate_name, examples),
        "production": _score("gemma-4-e4b-decision", examples),
        "zero_shot_baseline": _score("gemma-4-e4b", examples),
    }
    print(json.dumps(results, indent=2))

    won = results["candidate"]["mean_abs_error_pct"] < results["production"]["mean_abs_error_pct"]
    print("candidate_wins" if won else "candidate_does_not_win")


if __name__ == "__main__":
    main()

"""Step 1 (docs/architecture.md): query thelook_ecommerce for the decision
model's features, split train/eval, write JSONL to GCS.

Label is the real historical outcome (order_items.status = 'Returned'), not a
synthetic one. Each example is a chat-format record matching decide.py's own
prompt shape, so fine-tuning the decision LoRA doesn't require changing the
inference-side prompt at all -- same template, now with weights behind it
instead of zero-shot.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

from google.cloud import bigquery, storage

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
GCS_BUCKET = os.environ.get("MLOPS_GCS_BUCKET", f"{PROJECT_ID}-mlops")
EVAL_FRACTION = 0.15

# One labeled example per (order_item, category) -- return_rate/avg_price are
# the same category-level signal retrieval.py fetches live at inference time,
# so train-time and serve-time features stay comparable.
QUERY = """
WITH category_stats AS (
  SELECT
    p.category,
    COUNTIF(oi.status = 'Returned') / COUNT(*) AS category_return_rate,
    AVG(oi.sale_price) AS category_avg_price
  FROM `bigquery-public-data.thelook_ecommerce.order_items` oi
  JOIN `bigquery-public-data.thelook_ecommerce.products` p ON oi.product_id = p.id
  GROUP BY p.category
)
SELECT
  oi.id AS order_item_id,
  p.category,
  u.id AS user_id,
  u.age,
  u.gender,
  oi.sale_price,
  cs.category_return_rate,
  cs.category_avg_price,
  IF(oi.status = 'Returned', 1, 0) AS returned
FROM `bigquery-public-data.thelook_ecommerce.order_items` oi
JOIN `bigquery-public-data.thelook_ecommerce.products` p ON oi.product_id = p.id
JOIN `bigquery-public-data.thelook_ecommerce.users` u ON oi.user_id = u.id
JOIN category_stats cs ON cs.category = p.category
WHERE oi.status IN ('Returned', 'Complete', 'Shipped')
ORDER BY RAND()
LIMIT 20000
"""

_SYSTEM = (
    "You are a return-risk model for an online retailer. Score the likelihood "
    "this customer keeps (does not return) the item they're asking about, "
    "using ONLY the customer profile, category statistics, and policy context "
    "given. Cite the specific signal driving your score in the rationale."
)


def _to_example(row: bigquery.table.Row) -> dict:
    keep_rate = 1 - row.category_return_rate
    risk_category = "low" if keep_rate > 0.85 else "medium" if keep_rate > 0.65 else "high"
    target = {
        "keep_confidence_pct": round(keep_rate * 100),
        "risk_category": risk_category,
        "rationale": (
            f"Category '{row.category}' has a historical return rate of "
            f"{row.category_return_rate:.0%}."
        ),
    }
    human = (
        f"Customer profile: age {row.age}, gender {row.gender}\n"
        f"Category stats: return_rate={row.category_return_rate:.3f}, "
        f"avg_price={row.category_avg_price:.2f}\n"
        "Policy context:\n(see data/rag_corpus for the category policy doc)\n"
        f"Customer message: Considering a ${row.sale_price:.2f} item in {row.category}.\n"
        "Note already drafted for the customer: (drafting model output, not reproduced here)"
    )
    return {
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": human},
            {"role": "assistant", "content": json.dumps(target)},
        ]
    }


def main() -> None:
    bq = bigquery.Client(project=PROJECT_ID)
    rows = list(bq.query(QUERY).result())
    if not rows:
        raise RuntimeError("Query returned no rows -- check BigQuery access/project.")

    examples = [_to_example(r) for r in rows]
    random.shuffle(examples)
    split = int(len(examples) * (1 - EVAL_FRACTION))
    train, eval_ = examples[:split], examples[split:]

    out_dir = Path("mlops/_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "train.jsonl"
    eval_path = out_dir / "eval.jsonl"
    train_path.write_text("\n".join(json.dumps(e) for e in train))
    eval_path.write_text("\n".join(json.dumps(e) for e in eval_))

    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET)
    uploads = [(train_path, "decision/train.jsonl"), (eval_path, "decision/eval.jsonl")]
    for local_path, blob_name in uploads:
        bucket.blob(blob_name).upload_from_filename(local_path)
        print(f"Uploaded {local_path} -> gs://{GCS_BUCKET}/{blob_name}")

    print(f"{len(train)} train / {len(eval_)} eval examples")


if __name__ == "__main__":
    main()

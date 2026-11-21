"""Sample a small, varied pool of thelook_ecommerce users and precompute a short
natural-language summary for each, so the frontend's persona picker never computes
anything on the request path.

Run once (or whenever you want a fresh sample): writes data/personas.json.
Requires `gcloud auth application-default login` for BigQuery access.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from google.cloud import bigquery

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "personas.json"

QUERY = """
WITH user_stats AS (
  SELECT
    u.id AS user_id,
    u.first_name,
    u.age,
    u.gender,
    u.city,
    u.state,
    COUNT(DISTINCT oi.order_id) AS num_orders,
    SUM(oi.sale_price) AS total_spent,
    COUNTIF(oi.status = 'Returned') AS num_returned,
    APPROX_TOP_COUNT(p.category, 1)[OFFSET(0)].value AS top_category
  FROM `bigquery-public-data.thelook_ecommerce.users` u
  JOIN `bigquery-public-data.thelook_ecommerce.order_items` oi ON u.id = oi.user_id
  JOIN `bigquery-public-data.thelook_ecommerce.products` p ON oi.product_id = p.id
  GROUP BY u.id, u.first_name, u.age, u.gender, u.city, u.state
  -- Real distribution: most users have 1 order, max is 4 (checked directly against
  -- the dataset) -- >=2 selects for some repeat history worth showing in a persona
  -- summary, while still leaving ~30k candidates to sample from.
  HAVING num_orders >= 2
)
SELECT *
FROM user_stats
ORDER BY RAND()
LIMIT 40
"""


def summarize(row: bigquery.table.Row) -> str:
    return_rate = row.num_returned / row.num_orders
    return (
        f"{row.first_name}, {row.age}, from {row.city}, {row.state}. "
        f"{row.num_orders} orders totaling ${row.total_spent:,.2f}, "
        f"{row.num_returned} returned ({return_rate:.0%} return rate). "
        f"Shops mostly in {row.top_category}."
    )


def main() -> None:
    client = bigquery.Client()
    rows = list(client.query(QUERY).result())
    if not rows:
        raise RuntimeError("Query returned no users — check BigQuery access/project.")

    personas = [
        {
            "user_id": row.user_id,
            "first_name": row.first_name,
            "age": row.age,
            "gender": row.gender,
            "city": row.city,
            "state": row.state,
            "num_orders": row.num_orders,
            "total_spent": round(row.total_spent, 2),
            "num_returned": row.num_returned,
            "top_category": row.top_category,
            "summary": summarize(row),
        }
        for row in rows
    ]
    random.shuffle(personas)

    OUTPUT_PATH.write_text(json.dumps(personas, indent=2))
    print(f"Wrote {len(personas)} personas to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

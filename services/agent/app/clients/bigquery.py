"""Direct BigQuery access for the agent service -- no separate feature-service
microservice (simplest option first, per docs/architecture.md).

Locally this uses the developer's own `gcloud auth application-default login`
credentials; in GKE it'll use that cluster's own Workload Identity binding
(separate from the GitHub Actions WIF used for deploy) -- not needed yet.
"""

from __future__ import annotations

import os
from functools import lru_cache

from google.cloud import bigquery

_QUERY = """
    SELECT
      COUNT(DISTINCT oi.order_id) AS num_orders,
      COUNTIF(oi.status = 'Returned') AS num_returned,
      AVG(oi.sale_price) AS avg_price
    FROM `bigquery-public-data.thelook_ecommerce.order_items` oi
    JOIN `bigquery-public-data.thelook_ecommerce.products` p ON oi.product_id = p.id
    WHERE p.category = @category
"""


@lru_cache(maxsize=64)
def get_category_stats(category: str) -> dict:
    # Explicit, not relying on GOOGLE_CLOUD_PROJECT being set -- our own env
    # var name (GCP_PROJECT_ID) is what .env/Secret Manager actually use.
    client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])
    job = client.query(
        _QUERY,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("category", "STRING", category)]
        ),
    )
    row = next(iter(job.result()))
    return_rate = row.num_returned / row.num_orders if row.num_orders else 0.0
    return {
        "category": category,
        "num_orders": row.num_orders,
        "return_rate": round(return_rate, 3),
        "avg_price": round(float(row.avg_price), 2) if row.avg_price else None,
    }

"""Step 6 (docs/architecture.md): POST /v1/load_lora_adapter (load_inplace=True)
against the running model-serving Deployment -- no pod restart.

vLLM's load endpoint takes a path on the *pod's own filesystem*, not a gs://
URI -- it doesn't fetch from GCS itself. The real wrinkle this script handles:
download the adapter from GCS locally, then `kubectl cp` it into the running
pod before calling the load endpoint. No PVC/init-container needed for a
demo-scale adapter.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import requests
from google.cloud import storage

NAMESPACE = os.environ.get("GKE_NAMESPACE", "vertex-demo")
MODEL_SERVING_URL = os.environ.get("MODEL_SERVING_URL", "http://model-serving.vertex-demo.svc.cluster.local:8000")
POD_ADAPTER_DIR = "/adapters/decision"


def _first_pod(label: str) -> str:
    out = subprocess.run(
        ["kubectl", "get", "pods", "-n", NAMESPACE, "-l", f"app={label}",
         "-o", "jsonpath={.items[0].metadata.name}"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def main() -> None:
    adapter_gcs_path = sys.argv[1]  # gs://bucket/prefix
    bucket_name, prefix = adapter_gcs_path.removeprefix("gs://").split("/", 1)

    with tempfile.TemporaryDirectory() as tmp:
        bucket = storage.Client().bucket(bucket_name)
        for blob in bucket.list_blobs(prefix=prefix):
            rel = blob.name.removeprefix(prefix).lstrip("/")
            if not rel:
                continue
            local_path = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(local_path) or tmp, exist_ok=True)
            blob.download_to_filename(local_path)

        pod = _first_pod("model-serving")
        subprocess.run(
            ["kubectl", "exec", "-n", NAMESPACE, pod, "--", "mkdir", "-p", POD_ADAPTER_DIR],
            check=True,
        )
        subprocess.run(
            ["kubectl", "cp", f"{tmp}/.", f"{NAMESPACE}/{pod}:{POD_ADAPTER_DIR}"],
            check=True,
        )

    resp = requests.post(
        f"{MODEL_SERVING_URL}/v1/load_lora_adapter",
        json={
            "lora_name": "gemma-4-e4b-decision",
            "lora_path": POD_ADAPTER_DIR,
            "load_inplace": True,
        },
        timeout=60,
    )
    resp.raise_for_status()
    print(f"Loaded adapter from {adapter_gcs_path} as 'gemma-4-e4b-decision'")


if __name__ == "__main__":
    main()

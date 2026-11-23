"""Step 4 (docs/architecture.md): upload_model() to Vertex AI Model Registry,
tagged `staging`. The registry entry is a versioning/metadata record for the
GCS adapter artifact -- actual serving stays the self-hosted vLLM deployment
in GKE, not a Vertex AI Endpoint, so serving_container_image_uri below is
only to satisfy the SDK's required field, never deployed.
"""

from __future__ import annotations

import os
import sys

import google.cloud.aiplatform as aiplatform

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION = os.environ.get("GCP_REGION", "us-central1")
MODEL_DISPLAY_NAME = "gemma-4-e4b-decision-lora"


def main() -> None:
    adapter_gcs_path = sys.argv[1]

    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    model = aiplatform.Model.upload(
        display_name=MODEL_DISPLAY_NAME,
        artifact_uri=adapter_gcs_path,
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.2-4:latest",
        version_aliases=["staging"],
    )
    print(f"Registered {model.resource_name} version {model.version_id}, aliased 'staging'")
    print(model.resource_name)


if __name__ == "__main__":
    main()

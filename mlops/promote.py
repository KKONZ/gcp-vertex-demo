"""Step 5 (docs/architecture.md): if the new version won evaluate.py's
comparison, reassign the `production` alias -- a metadata change, not a
redeploy. Actually swapping the running vLLM deployment's weights is
hotswap.py's job, triggered separately once this alias move is confirmed.
"""

from __future__ import annotations

import os
import sys

import google.cloud.aiplatform as aiplatform

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION = os.environ.get("GCP_REGION", "us-central1")


def main() -> None:
    model_resource_name = sys.argv[1]

    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    model = aiplatform.Model(model_resource_name)

    try:
        model.remove_version_aliases(["production"])  # no-op if this is the first promotion ever
    except Exception:  # noqa: BLE001
        pass
    model.add_version_aliases(["production"])
    model.remove_version_aliases(["staging"])
    print(f"{model_resource_name} version {model.version_id} is now 'production'")


if __name__ == "__main__":
    main()

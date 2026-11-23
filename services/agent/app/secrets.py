"""Runtime Secret Manager fallback -- makes docs/architecture.md's "App secrets
...read at runtime via the pod's own GKE Workload Identity" literally true.

Call once, before anything reads the env vars it fills in (same spot as
load_dotenv() in main.py). Local dev never hits this: .env already populates
OPENAI_API_KEY, so the loop below finds nothing missing and never imports the
Secret Manager client.
"""

from __future__ import annotations

import os

_SECRET_ENV_VARS = ["OPENAI_API_KEY"]


def _secret_id(env_var_name: str) -> str:
    return env_var_name.lower().replace("_", "-")


def load_secrets() -> None:
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        return

    missing = [name for name in _SECRET_ENV_VARS if not os.environ.get(name)]
    if not missing:
        return

    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    for name in missing:
        secret_name = f"projects/{project_id}/secrets/{_secret_id(name)}/versions/latest"
        response = client.access_secret_version(name=secret_name)
        os.environ[name] = response.payload.data.decode("utf-8")

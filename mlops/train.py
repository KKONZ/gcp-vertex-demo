"""Step 2 (docs/architecture.md): submit the QLoRA fine-tuning job as a
Vertex AI CustomJob -- one GPU, logged to Vertex AI Experiments. This is the
orchestration piece (job submission, machine/accelerator config, experiment
wiring); trainer/train_lora.py is what actually runs inside it.
"""

from __future__ import annotations

import os
import time

import google.cloud.aiplatform as aiplatform

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION = os.environ.get("GCP_REGION", "us-central1")
GCS_BUCKET = os.environ.get("MLOPS_GCS_BUCKET", f"{PROJECT_ID}-mlops")
EXPERIMENT = "gcp-vertex-demo-decision-lora"


def main() -> None:
    aiplatform.init(project=PROJECT_ID, location=LOCATION, staging_bucket=f"gs://{GCS_BUCKET}")

    run_name = f"decision-lora-{int(time.time())}"
    output_dir = f"gs://{GCS_BUCKET}/decision-lora/{run_name}"

    job = aiplatform.CustomJob.from_local_script(
        display_name=run_name,
        script_path="mlops/trainer/train_lora.py",
        container_uri="us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest",
        requirements=open("mlops/trainer/requirements.txt").read().splitlines(),
        args=[
            f"--train-file=gs://{GCS_BUCKET}/decision/train.jsonl",
            f"--eval-file=gs://{GCS_BUCKET}/decision/eval.jsonl",
            f"--output-dir={output_dir}",
            f"--experiment={EXPERIMENT}",
            f"--run-name={run_name}",
            f"--project={PROJECT_ID}",
            f"--location={LOCATION}",
        ],
        replica_count=1,
        machine_type="g2-standard-8",
        accelerator_type="NVIDIA_L4",
        accelerator_count=1,
    )
    job.run(sync=True)

    print(f"Adapter written to {output_dir}")
    print(output_dir)  # last line: callers (orchestrate.py) capture this


if __name__ == "__main__":
    main()

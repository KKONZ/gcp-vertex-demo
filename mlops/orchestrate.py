"""Runs the full fine-tune -> evaluate -> register -> promote -> hotswap
pipeline in order. One sequential script against the Vertex AI SDK, not a
full Vertex AI Pipelines (KFP) DAG -- docs/architecture.md calls out that the
scheduling/reusability a KFP DAG buys isn't needed for this demo.

Each step is also independently runnable (see its own __main__) for
debugging a single stage without rerunning the whole thing.
"""

from __future__ import annotations

import subprocess
import sys


def _run(cmd: list[str]) -> str:
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    print(result.stdout)
    return result.stdout.strip()


def main() -> None:
    _run([sys.executable, "mlops/prepare_data.py"])

    train_output = _run([sys.executable, "mlops/train.py"])
    adapter_gcs_path = train_output.splitlines()[-1]

    eval_output = _run([sys.executable, "mlops/evaluate.py", "mlops/_data/eval.jsonl"])
    if eval_output.splitlines()[-1] != "candidate_wins":
        print("Candidate did not beat production -- stopping before register/promote.")
        return

    register_output = _run([sys.executable, "mlops/register.py", adapter_gcs_path])
    model_resource_name = register_output.splitlines()[-1]

    _run([sys.executable, "mlops/promote.py", model_resource_name])
    _run([sys.executable, "mlops/hotswap.py", adapter_gcs_path])

    print("Pipeline complete: new decision adapter is live in production.")


if __name__ == "__main__":
    main()

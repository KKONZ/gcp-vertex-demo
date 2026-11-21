# Architecture

## Concept

Retailers already build after-the-fact loss-prevention tools to flag risky returns —
every large retailer's ops team has one. The reframe here: use the same return-risk model
proactively and consumer-facing, as a pre-purchase confidence score ("customers with your
profile kept 92% of items like this") instead of a post-purchase fraud flag. Same model,
opposite product — it reduces returns while reading as a styling assistant, not a loss-
prevention tool.

- **Data source:** [`thelook_ecommerce`](https://console.cloud.google.com/marketplace/product/bigquery-public-data/thelook-ecommerce) (BigQuery public dataset) — queried live, never copied into the repo.
- **Decision task:** predict return risk at order time, trained on the real historical label `order_items.status = 'Returned'`.

## Model & serving stack

| Role | Primary | Serving | Fallback |
|---|---|---|---|
| Drafting / reasoning | Gemma 4 E4B, zero-shot | Self-hosted vLLM | OpenAI |
| Decision (return-risk) | Gemma 4 E4B + fine-tuned LoRA | Same vLLM deployment, second adapter (multi-LoRA) | OpenAI, zero-shot approximation |
| Embeddings | EmbeddingGemma 2 | Self-hosted vLLM, pooling runner | *none — deliberate* |
| Voice (stretch) | Whisper | Self-hosted vLLM | OpenAI Whisper API |

Drafting and decision share **one** vLLM deployment of Gemma 4 E4B — base weights loaded
once, two LoRA adapters swapped per request — rather than two separate deployments.

**Why embeddings get no fallback:** a managed embedding API would produce vectors from a
different embedding space than everything already stored in pgvector. Mixed-space
nearest-neighbor search fails silently, not loudly — the one place resilience would
introduce a correctness bug, not a safety net.

**Fallback mechanics:** LangChain `Runnable.with_fallbacks()`, with an explicit `timeout=`
on the primary client (a merely-slow call never raises on its own, so it never fails over
without one) and `exceptions_to_handle` scoped to transient failures only, not a blanket
catch that would also mask real bugs as "degraded gracefully."

## Retrieval & multimodal input

- **Vector store:** pgvector, self-hosted Postgres in-cluster (StatefulSet + PVC).
- **RAG corpus:** authored category-level policy / fraud-indicator documents (`data/rag_corpus/`) — the decision output cites these.
- **Vision input (stretch):** the uploaded photo is embedded directly through EmbeddingGemma 2 and matched via cross-modal similarity against the product-text embeddings already in pgvector — no captioning hop, since `thelook_ecommerce` has no catalog images to caption against anyway.

## Frontend & demo identity

- **Frontend:** Streamlit, standing in for "the mobile app."
- **Demo identity:** `data/scripts/sample_personas.py` samples a small pool of `thelook` users offline and precomputes a short summary for each → `data/personas.json`. The app picks one at random per session — no live computation on the critical path.
- **Data access:** the agent service queries BigQuery directly for order/user/product features — no separate feature-service microservice.

## Infrastructure

Kubernetes throughout, split by what each cluster is good for proving:

- **Local cluster** (`kind` / Docker Desktop) proves the CPU-only pieces: orchestrator, pgvector, frontend, CI.
- **GKE Autopilot** (Terraform-provisioned) proves GPU-backed self-hosted inference — Autopilot supports requesting `nvidia-l4` / `nvidia-tesla-t4` GPUs directly in the pod spec.

This machine's own GPU has 4GB VRAM, below Gemma 4 E4B's ~6.2GB footprint at 4-bit — it
genuinely doesn't fit. Locally, self-hosted model calls fail fast and exercise the
`with_fallbacks()` path for real; GPU-backed inference is validated on GKE in a short
window, not left running continuously.

## CI/CD & secrets

- **On every push:** lint, test, build images, push to Artifact Registry.
- **Deploy** (`workflow_dispatch`, manual): authenticates via **Workload Identity Federation** — no service-account key stored anywhere. Already provisioned against the project backing this repo (project ID intentionally not listed here -- see the gitignored local setup notes):
  - Workload identity pool/provider `github-pool`/`github-provider`, trusting GitHub's OIDC issuer, attribute-condition pinned to `assertion.repository=='KKONZ/gcp-vertex-demo'`.
  - Deploy service account `github-deployer@<project-id>.iam.gserviceaccount.com`, holding exactly `roles/container.admin` and `roles/artifactregistry.writer`.
- **Teardown** (scheduled): scales GPU-backed deployments to zero on a recurring schedule.
- **App secrets** (e.g. `OPENAI_API_KEY`): GCP Secret Manager, read at runtime via the pod's own GKE Workload Identity (a separate binding from the GitHub Actions WIF above) — never in the image, never in the repo.

**Why this is safe against the usual public-repo attack surface:** a fork's workflow runs
carry the fork's own `repository` claim, so the pinned attribute-condition above rejects
them. A `pull_request`-triggered run from an external contributor gets a read-only token
and is never granted `id-token: write`, even if requested — GitHub's own default. The one
real risk is `pull_request_target` combined with `id-token: write` (the "pwn request"
pattern) — hard rule: the WIF auth step only ever lives in a `workflow_dispatch` job or a
protected-branch `push`, never `pull_request_target`.

## MLOps: fine-tuning & promotion (stretch goal)

Built from managed Vertex AI primitives rather than custom infrastructure:

1. **Data prep** — query `thelook_ecommerce` for the decision model's features, split train/eval, write JSONL to GCS.
2. **Train** — Vertex AI Custom Training Job, one GPU, QLoRA on Gemma 4 E4B (~9GB — fits an L4 or T4). Logged to Vertex AI Experiments.
3. **Evaluate** — score against current production and the zero-shot baseline on held-out real orders.
4. **Register** — `upload_model()` to Vertex AI Model Registry, tagged `staging`.
5. **Promote** — if the new version wins, reassign the `production` alias — a metadata change, not a redeploy.
6. **Serve** — `POST /v1/load_lora_adapter` (`load_inplace=True`) hot-swaps the running vLLM deployment's adapter, no pod restart.

Orchestration: one sequential Python script against the Vertex AI SDK, not a full Vertex
AI Pipelines (KFP) DAG — that buys scheduling/reusability this demo doesn't need.

## Scope: MVP vs. stretch

MVP = text-only RAG + a baseline (not-yet-fine-tuned) decision function + local K8s
validated + green CI. The app itself focuses on hosting/serving.

Stretch goals, in priority order: (1) fine-tune the decision LoRA adapter externally and
swap it in behind the existing seam; (2) vision input; (3) voice input; (4) a full live
GPU validation / demo on GKE.

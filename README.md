# gcp-vertex-demo

A return-risk agent for e-commerce, built on real order data from the public
`thelook_ecommerce` dataset: instead of flagging risky orders after the fact, it surfaces
a confidence score *before* checkout, grounded in retrieved policy context and the
customer's own history.

See [`docs/architecture.md`](docs/architecture.md) for the full design — model/serving
stack, retrieval, infrastructure, CI/CD, and the MLOps fine-tuning path.

## Status

Agent core (LangGraph + FastAPI) and Streamlit frontend run both as plain local
processes and in Kubernetes (local `kind` or GKE Autopilot); see `docs/architecture.md`
for the full design. Self-hosted model serving (vLLM) and the MLOps fine-tuning pipeline
are scaffolded but unverified against a live GPU — see `services/model-serving`,
`services/embedding-service`, and `mlops/` for the caveats called out in each.

## Running it locally

```bash
# 1. pgvector
docker run -d --name pgvector -e POSTGRES_PASSWORD=postgres -p 5432:5432 pgvector/pgvector:pg16

# 2. load the RAG corpus
python data/scripts/load_rag_corpus.py

# 3. sample demo personas (requires `gcloud auth application-default login`)
python data/scripts/sample_personas.py

# 4. agent service
cd services/agent && uvicorn app.main:app --reload

# 5. frontend, in another shell
streamlit run services/frontend/app.py
```

Requires a `.env` (gitignored, including `.env.example` -- not committed, to avoid
publishing a real GCP project ID) with:

```
OPENAI_API_KEY=
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
GCP_PROJECT_ID=<your-gcp-project-id>
BIGQUERY_LOCATION=US
```

## Running it in Kubernetes

### Local (`kind`)

```bash
kind create cluster --name vertex-demo
docker build -f services/agent/Dockerfile -t agent:local .
docker build -f services/frontend/Dockerfile -t frontend:local .
kind load docker-image agent:local frontend:local --name vertex-demo

bash infra/k8s/load-personas-configmap.sh        # from data/personas.json
bash infra/k8s/overlays/kind/load-secrets.sh      # OPENAI_API_KEY + your ADC file

kubectl apply -k infra/k8s/overlays/kind
kubectl -n vertex-demo rollout status deployment/agent
kubectl -n vertex-demo port-forward svc/frontend 8501:8501

# first time only: rag_documents starts empty
kubectl -n vertex-demo port-forward svc/pgvector 15432:5432 &
DATABASE_URL=postgresql://postgres:postgres@localhost:15432/postgres \
  python data/scripts/load_rag_corpus.py
```

**After code changes**, rebuild with a *new* tag rather than reusing `agent:local` --
once a tag has been loaded into a kind node once, re-loading the same tag with new
content is unreliable (kubelet/containerd don't always pick up the new digest for a
name they've already cached), and silently running stale code is a much worse failure
mode than an explicit new tag:

```bash
TAG=agent:$(git rev-parse --short HEAD)-$(date +%s)
docker build -f services/agent/Dockerfile -t "$TAG" .
kind load docker-image "$TAG" --name vertex-demo
kubectl -n vertex-demo set image deployment/agent agent="$TAG"
```

This proves the CPU-only path: agent, frontend, and pgvector in-cluster, BigQuery via
your own `gcloud auth application-default login` credentials, OpenAI as the only model
backend that actually resolves (self-hosted still points nowhere, same as plain local dev).

### GKE Autopilot

Provisioned via Terraform (`infra/terraform/`) — GKE Autopilot cluster, Artifact
Registry, Secret Manager, and the `agent-workload` Workload Identity binding. The
GitHub Actions WIF trust (`github-pool`/`github-provider`, `github-deployer` SA) is
provisioned separately and already live against this repo's project.

```bash
cd infra/terraform
terraform init
terraform plan   # review before applying -- creates a real billable cluster
terraform apply
```

Then deploy manually (`kubectl apply -k infra/k8s/overlays/gke`, after building/pushing
images to the Terraform-created Artifact Registry repo) or via the `workflow_dispatch`
`deploy.yml` GitHub Action, which authenticates over WIF — no service-account key
anywhere. `teardown.yml` runs nightly to scale the GPU-backed `model-serving` /
`embedding-service` deployments to zero.

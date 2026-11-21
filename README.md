# gcp-vertex-demo

A return-risk agent for e-commerce, built on real order data from the public
`thelook_ecommerce` dataset: instead of flagging risky orders after the fact, it surfaces
a confidence score *before* checkout, grounded in retrieved policy context and the
customer's own history.

See [`docs/architecture.md`](docs/architecture.md) for the full design — model/serving
stack, retrieval, infrastructure, CI/CD, and the MLOps fine-tuning path.

## Status

Early build. Currently working: local-only agent core (LangGraph + FastAPI) and a
Streamlit frontend, running against pgvector and OpenAI (no self-hosted models or
Kubernetes yet — those come next; see `docs/architecture.md` for the full roadmap).

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

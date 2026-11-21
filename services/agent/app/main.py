import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # before any client module reads env vars, even lazily

from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app.graph import build_graph  # noqa: E402

# Default assumes the local-dev repo layout (services/agent/app/main.py, 4
# levels under the repo root); PERSONAS_PATH overrides it for Docker/K8s,
# where the directory depth is different (see Dockerfile).
PERSONAS_PATH = Path(
    os.environ.get("PERSONAS_PATH")
    or Path(__file__).resolve().parents[3] / "data" / "personas.json"
)

app = FastAPI(title="gcp-vertex-demo agent")
graph = build_graph()


def _load_personas() -> dict[int, dict]:
    if not PERSONAS_PATH.exists():
        return {}
    return {p["user_id"]: p for p in json.loads(PERSONAS_PATH.read_text())}


class AssessRequest(BaseModel):
    user_id: int
    category: str
    message: str


@app.get("/personas")
def list_personas():
    return list(_load_personas().values())


@app.post("/assess")
def assess(req: AssessRequest):
    persona = _load_personas().get(req.user_id)
    persona_summary = persona["summary"] if persona else "Unknown customer, no history available."

    result = graph.invoke(
        {
            "user_id": req.user_id,
            "persona_summary": persona_summary,
            "category": req.category,
            "message": req.message,
        }
    )
    return {
        "draft": result["draft"],
        "decision": result["decision"],
        "sources": [d["source"] for d in result["retrieved_docs"]],
    }

"""Embed data/rag_corpus/*.md and load into pgvector.

Each file is one chunk — these are short, deliberately-written docs (a few
paragraphs each), not long manuals that need splitting.

Run after pgvector is up (see README) and before starting the agent service.
"""

from __future__ import annotations

import sys
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent.parent / "rag_corpus"

# Load .env and make the agent app's clients importable without installing it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "services" / "agent"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.clients.embeddings import embed_texts  # noqa: E402
from app.clients.pgvector import ensure_schema, get_connection, upsert_document  # noqa: E402


def main() -> None:
    files = sorted(CORPUS_DIR.glob("*.md"))
    if not files:
        raise RuntimeError(f"No markdown files found in {CORPUS_DIR}")

    contents = [f.read_text() for f in files]
    embeddings = embed_texts(contents)

    conn = get_connection()
    ensure_schema(conn)
    for f, content, embedding in zip(files, contents, embeddings):
        upsert_document(conn, source=f.name, content=content, embedding=embedding)
        print(f"loaded {f.name}")

    print(f"Loaded {len(files)} documents into pgvector.")


if __name__ == "__main__":
    main()

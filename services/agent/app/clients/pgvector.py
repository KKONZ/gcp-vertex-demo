"""Thin client over the self-hosted pgvector instance.

One table for now: rag_documents. No ORM — this is a handful of queries, an ORM
would be an abstraction with nothing to abstract over yet.
"""

from __future__ import annotations

import os

import psycopg
from pgvector.psycopg import register_vector

from .embeddings import EMBEDDING_DIM


def get_connection() -> psycopg.Connection:
    # Read lazily, not at import time: whoever imports this module shouldn't have
    # to have already called load_dotenv() first just to make the import succeed.
    conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag_documents (
            id SERIAL PRIMARY KEY,
            source TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding VECTOR({EMBEDDING_DIM}) NOT NULL
        )
        """
    )


def upsert_document(conn: psycopg.Connection, source: str, content: str, embedding: list[float]) -> None:
    conn.execute("DELETE FROM rag_documents WHERE source = %s", (source,))
    conn.execute(
        "INSERT INTO rag_documents (source, content, embedding) VALUES (%s, %s, %s)",
        (source, content, embedding),
    )


def search(conn: psycopg.Connection, query_embedding: list[float], limit: int = 3) -> list[dict]:
    # The target column's declared type drives an implicit cast on INSERT, but
    # there's no such context here -- without the explicit ::vector cast, a
    # plain Python list gets sent as double precision[], which <=> rejects.
    rows = conn.execute(
        """
        SELECT source, content, 1 - (embedding <=> %s::vector) AS similarity
        FROM rag_documents
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (query_embedding, query_embedding, limit),
    ).fetchall()
    return [{"source": r[0], "content": r[1], "similarity": r[2]} for r in rows]

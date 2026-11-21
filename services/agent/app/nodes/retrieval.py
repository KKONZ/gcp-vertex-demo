from app.clients.bigquery import get_category_stats
from app.clients.embeddings import embed_query
from app.clients.pgvector import get_connection, search


def retrieve(state: dict) -> dict:
    conn = get_connection()
    query_vec = embed_query(f"{state['category']}: {state['message']}")
    docs = search(conn, query_vec, limit=3)
    stats = get_category_stats(state["category"])
    return {"retrieved_docs": docs, "category_stats": stats}

"""EmbeddingGemma 2, loaded in-process via sentence-transformers for now.

This is the local-dev phase: the real architecture serves this model from its own
vLLM deployment (see docs/architecture.md), but that container doesn't exist yet
(it's a later milestone). Running the same model in-process here means retrieval
actually works end-to-end today, and the only thing that changes when the vLLM
service lands is *how* this function calls the model, not which model it calls or
what it returns — so vectors stay comparable across that transition.

Deliberately has no fallback provider: a different embedding model would place
vectors in a different space than everything already stored in pgvector, which
breaks nearest-neighbor search silently rather than loudly.
"""

from __future__ import annotations

from functools import lru_cache

EMBEDDING_DIM = 768


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("google/embeddinggemma-2")


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = _model().encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]

"""Model client wiring: self-hosted primary, OpenAI fallback -- everywhere
except embeddings (see clients/embeddings.py for why that one has no fallback).

There's no self-hosted vLLM endpoint actually running in local dev yet -- that's
deliberate. SELF_HOSTED_MODEL_URL points at a deployment that doesn't exist on
this machine, so the primary call fails fast (short timeout, no retries) and
the fallback fires for real, exercising the exact mechanism that matters once
the real vLLM service lands (see docs/architecture.md).
"""

from __future__ import annotations

import os
from typing import TypeVar

import openai
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

SELF_HOSTED_BASE_URL = os.environ.get("SELF_HOSTED_MODEL_URL", "http://localhost:8001/v1")
SELF_HOSTED_TIMEOUT = float(os.environ.get("SELF_HOSTED_TIMEOUT_SECONDS", "3"))

# Scoped to transient failures only, not malformed-input/validation errors --
# a blanket `Exception` catch would mask real bugs as "degraded gracefully."
TRANSIENT_EXCEPTIONS = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
)

T = TypeVar("T", bound=BaseModel)


def _self_hosted(model_name: str, temperature: float = 0.2) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=SELF_HOSTED_BASE_URL,
        api_key="not-needed",
        model=model_name,
        temperature=temperature,
        timeout=SELF_HOSTED_TIMEOUT,
        max_retries=0,
    )


def _openai(temperature: float = 0.2) -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o-mini", temperature=temperature)


def drafting_model():
    primary = _self_hosted("gemma-4-e4b")
    fallback = _openai()
    return primary.with_fallbacks([fallback], exceptions_to_handle=TRANSIENT_EXCEPTIONS)


def decision_model(schema: type[T]):
    """Returns a runnable producing `schema`. `with_structured_output` has to be
    applied to each chat model *before* `with_fallbacks` -- `RunnableWithFallbacks`
    doesn't expose that method, since it's chat-model-specific, not generic."""
    primary = _self_hosted("gemma-4-e4b-decision").with_structured_output(schema)
    fallback = _openai().with_structured_output(schema)
    return primary.with_fallbacks([fallback], exceptions_to_handle=TRANSIENT_EXCEPTIONS)

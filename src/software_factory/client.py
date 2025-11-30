"""Client factory helpers for Microsoft Agent Framework chat clients."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from agent_framework.openai import OpenAIChatClient


class MissingAPIKeyError(RuntimeError):
    """Raised when OPENAI_API_KEY is not configured."""


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def _require_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise MissingAPIKeyError(
            "OPENAI_API_KEY is not set; export it before building the workflow."
        )
    return api_key


@lru_cache(maxsize=4)
def _build_client(model_id: str) -> OpenAIChatClient:
    api_key = _require_api_key()
    return OpenAIChatClient(api_key=api_key, model_id=model_id)


def get_chat_client(model_override: Optional[str] = None) -> OpenAIChatClient:
    """Return a cached OpenAI chat client configured for Microsoft Agent Framework."""

    model_id = model_override or DEFAULT_MODEL
    return _build_client(model_id)

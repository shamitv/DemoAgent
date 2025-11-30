"""Client factory helpers for Microsoft Agent Framework chat clients."""

from __future__ import annotations

import os
import logging
import sys
from functools import lru_cache
from typing import Optional

from agent_framework.openai import OpenAIChatClient


class MissingAPIKeyError(RuntimeError):
    """Raised when OPENAI_API_KEY is not configured."""


DEFAULT_MODEL_FALLBACK = "gpt-4o"
_LOGGER = logging.getLogger(__name__)
if not _LOGGER.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[software-factory] %(message)s"))
    _LOGGER.addHandler(handler)
_LOGGER.setLevel(logging.INFO)
_LOGGER.propagate = False


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
    _LOGGER.info("Initializing OpenAI chat client with model %s", model_id)
    return OpenAIChatClient(api_key=api_key, model_id=model_id)


def _resolve_model_id(model_override: Optional[str]) -> str:
    """Pick a model honoring runtime env overrides loaded after import."""

    if model_override:
        return model_override
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL_FALLBACK)


def get_chat_client(model_override: Optional[str] = None) -> OpenAIChatClient:
    """Return a cached OpenAI chat client configured for Microsoft Agent Framework."""

    model_id = _resolve_model_id(model_override)
    return _build_client(model_id)

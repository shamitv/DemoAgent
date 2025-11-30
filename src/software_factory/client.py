"""Client factory helpers for Microsoft Agent Framework chat clients."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Mapping, Optional

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


@dataclass(frozen=True)
class ModelConfig:
    """Declarative capabilities per OpenAI chat model."""

    model_id: str
    forced_parameters: Dict[str, Any] = field(default_factory=dict)
    disallowed_parameters: frozenset[str] = frozenset()

    def apply(self, params: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        base = params or {}
        sanitized = {
            key: value
            for key, value in base.items()
            if value is not None and key not in self.disallowed_parameters
        }
        sanitized.update(self.forced_parameters)
        return sanitized

    def allows(self, parameter: str) -> bool:
        return parameter not in self.disallowed_parameters


DEFAULT_MODEL_CONFIG = ModelConfig(model_id="default")
MODEL_CONFIGS: Dict[str, ModelConfig] = {
    "gpt-4o": ModelConfig(model_id="gpt-4o"),
    "gpt-4.1": ModelConfig(model_id="gpt-4.1"),
    "gpt-5-mini": ModelConfig(model_id="gpt-5-mini", disallowed_parameters=frozenset({"temperature","top_p"})),
}


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


def _build_model_config(
    model_id: str, overrides: Optional[Dict[str, Any]] = None
) -> ModelConfig:
    base = MODEL_CONFIGS.get(model_id, ModelConfig(model_id=model_id))
    forced = dict(base.forced_parameters)
    disallowed = set(base.disallowed_parameters)
    if overrides:
        forced.update(overrides.get("forced_parameters", {}))
        disallowed.update(overrides.get("disallowed_parameters", []))
        allowed = overrides.get("allow_parameters")
        if allowed:
            disallowed -= set(allowed)
    return ModelConfig(model_id=model_id, forced_parameters=forced, disallowed_parameters=frozenset(disallowed))


def get_model_config(
    model_override: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> ModelConfig:
    """Lookup a model configuration, optionally applying overrides."""

    model_id = _resolve_model_id(model_override)
    return _build_model_config(model_id, overrides)


def apply_model_config(
    model_config: Optional[ModelConfig], params: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    """Drop unsupported params and enforce forced values for ChatAgent kwargs."""

    config = model_config or DEFAULT_MODEL_CONFIG
    return config.apply(params)


def get_chat_client(model_override: Optional[str] = None) -> OpenAIChatClient:
    """Return a cached OpenAI chat client configured for Microsoft Agent Framework."""

    model_id = _resolve_model_id(model_override)
    return _build_client(model_id)

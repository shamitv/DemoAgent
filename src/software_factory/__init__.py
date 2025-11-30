"""Software factory package powered by the Microsoft Agent Framework."""

from .client import get_chat_client
from .workflow import build_workflow

__all__ = ["get_chat_client", "build_workflow"]

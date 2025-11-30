"""Command-line entry point for running the software factory workflow."""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from agent_framework._workflows._events import (
    AgentRunEvent,
    AgentRunUpdateEvent,
    WorkflowFailedEvent,
    WorkflowOutputEvent,
    WorkflowStatusEvent,
    WorkflowWarningEvent,
)

from . import build_workflow, get_chat_client
from .client import MissingAPIKeyError, get_model_config


def _load_env_file(env_path: Path) -> None:
    """Populate os.environ from a .env file if present without overriding existing vars."""

    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key or key in os.environ:
            continue
        normalized = value.strip().strip('"').strip("'")
        os.environ[key] = normalized


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="software-factory",
        description="Run or debug the Microsoft Agent Framework software factory workflow.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Inline prompt to seed the planner (ignored if --prompt-file is provided).",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="Path to a text/markdown file whose contents seed the planner.",
    )
    parser.add_argument(
        "--model",
        help="Override the default OPENAI_MODEL when instantiating the chat client.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print every workflow event for debugging.",
    )
    return parser.parse_args(argv)


async def _run_workflow(prompt: str, model: Optional[str], debug: bool) -> str:
    model_config = get_model_config(model)
    chat_client = get_chat_client(model)
    workflow = build_workflow(chat_client, model_config=model_config)

    final_output: str = ""
    async for event in workflow.run_stream(prompt):
        if isinstance(event, WorkflowOutputEvent):
            final_output = str(event.data)
            print(f"[workflow-output:{event.source_executor_id}]\n{final_output}\n")
        elif isinstance(event, WorkflowFailedEvent):
            details = event.details
            raise RuntimeError(
                f"Workflow failed in executor {details.executor_id}: {details.error_type}: {details.message}"
            )
        elif debug:
            _debug_print(event)

    return final_output


def _debug_print(event) -> None:  # pragma: no cover - debug helper
    if isinstance(event, WorkflowStatusEvent):
        message = f"state={event.state.value}"
    elif isinstance(event, WorkflowWarningEvent):
        message = f"warning={event.data}"
    elif isinstance(event, AgentRunUpdateEvent):
        chunk = getattr(event.data, "delta", None)
        message = f"token={getattr(chunk, 'content', '')!r} executor={event.executor_id}"
    elif isinstance(event, AgentRunEvent):
        message = f"response executor={event.executor_id}"
    else:
        payload = getattr(event, "data", None)
        message = f"data={payload!r}"

    sys.stderr.write(f"[DEBUG][{event.__class__.__name__}] {message}\n")


def _load_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return args.prompt_file.read_text(encoding="utf-8")
    if args.prompt:
        return args.prompt
    raise SystemExit("Provide a prompt argument or --prompt-file path.")


def main(argv: Optional[list[str]] = None) -> int:
    _load_env_file(Path(".env"))
    args = _parse_args(argv)

    try:
        prompt = _load_prompt(args)
        final_output = asyncio.run(_run_workflow(prompt, args.model, args.debug))
        if not final_output:
            print("Workflow completed without explicit output. Check DEBUG logs for details.")
        return 0
    except MissingAPIKeyError as exc:
        sys.stderr.write(f"[ERROR] {exc}\n")
    except RuntimeError as exc:
        sys.stderr.write(f"[ERROR] {exc}\n")
    except KeyboardInterrupt:
        sys.stderr.write("[INFO] Workflow interrupted by user.\n")
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
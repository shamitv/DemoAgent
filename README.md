# Microsoft Agent Framework Software Factory

This repository is a demo of the Microsoft Agent Framework that implements the Planner -> Dispatcher -> Implementation -> Verification workflow described in `docs/agent_plan.md`. It targets the Microsoft Agent Framework using OpenAI models, following the "software factory" architecture that combines typed shared state, deterministic routing, and iterative verification loops.

## Getting Started

1. **Python**: Install Python 3.11 or newer.
2. **Dependencies**: Create a virtual environment and install the project in editable mode: `pip install -e .[dev]`.
3. **Environment Variables**:
   - `OPENAI_API_KEY`: Standard OpenAI API key.
   - `OPENAI_MODEL`: Optional override for the default `gpt-4o` model ID.
  - Model-specific tuning locks live in `software_factory.client.MODEL_CONFIGS`.
    Call `get_model_config(..., overrides={...})` before `build_workflow` if you need to
    force/allow parameters (e.g., disabling `temperature` for `gpt-5-mini`).

## Usage

### CLI run/debug

```
pip install -e .
# optionally place OPENAI_API_KEY inside a .env file
software-factory "Ship the feature" --debug
```

Use `--prompt-file docs/request.md` to seed the workflow from a file, and `--model gpt-4.1` to override `OPENAI_MODEL` for a single run. The CLI automatically loads environment variables from a local `.env` file before execution without overwriting already-exported variables.

### Programmatic usage

```python
import asyncio

from software_factory import build_workflow, get_chat_client


async def main():
  chat_client = get_chat_client()
  workflow = build_workflow(chat_client)
  async for event in workflow.run_stream("Implement the requested feature"):
    print(event)


asyncio.run(main())
```

Executors communicate exclusively through structured signals so that the Workflow graph enforces deterministic routing. The dispatcher also emits the final artifact via `WorkflowOutputEvent` once every task passes verification.

## Project Layout

```
src/
  software_factory/
    executors/
    __init__.py
    client.py
    state.py
    workflow.py

tests/
  test_placeholder.py
```

## Next Steps

- Connect workflow execution to a CLI or service host (FastAPI, MCP server, etc.).
- Expand the test suite with additional executor and integration coverage using agent stubs.
- Configure checkpointing storage for long-running deployments.

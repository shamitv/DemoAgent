# Architecting Autonomous Software Factories

*Based on "Architecting Autonomous Software Factories: A Definitive Guide to the Microsoft Agent Framework"*

## Executive Summary

The Microsoft Agent Framework (MAF) unifies AutoGen's agent autonomy with Semantic Kernel's rigor by orchestrating agents through explicit workflow graphs. This repository implements the Planner -> Dispatcher -> Implementation -> Verification software factory that leverages typed shared memory, deterministic routing, and iterative feedback loops to achieve reliable autonomous code production.

## Key Architectural Principles

1. **Graph-Based Workflow**: Executors are linked via directed edges, ensuring deterministic control flow while the LLM handles content generation.
2. **Stateless Agents, Stateful Ledger**: ChatAgents stay stateless; shared ProjectState stored in the workflow context carries all persistent data.
3. **Typed Memory with Pydantic**: Shared state models enforce schemas, preventing malformed hand-offs between agents.
4. **Deterministic Dispatcher**: A code-only dispatcher inspects state and routes execution to the correct executor, preventing stochastic drift.
5. **Verification Loop**: A dedicated Critic agent (or human) evaluates outputs, feeding failures back into the workflow for correction.

## Core Components To Implement

- **Client Factory**: `OpenAIChatClient` configured with API key + model overrides.
- **Shared State**: `Task` and `ProjectState` models plus helpers to read/write state from `WorkflowContext`.
- **Executors**:
  - `PlanningExecutor`: Generates structured plans and seeds shared state.
  - `DispatcherExecutor`: Implements content-based routing logic.
  - `ImplementationExecutor`: Focused agents (e.g., coder vs researcher) with optional tools.
  - `VerificationExecutor`: Applies the Reflexion pattern with pass/fail feedback.
- **Workflow Assembly**: `WorkflowBuilder` wiring planner -> dispatcher -> implementation/verifier cycles with proper signals.

## Environment Notes

- Python SDK package: `agent-framework` (latest release).
- Additional packages: `openai`, `pydantic`, test utilities.
- Authentication: standard OpenAI API key via `OPENAI_API_KEY` and optional `OPENAI_MODEL` override.

## Next Steps

Implement the above components under `src/software_factory/`, add automated tests in `tests/`, and document operational workflows in `README.md`.

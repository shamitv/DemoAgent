# Software Factory Architecture

This document summarizes the autonomous workflow implemented in this repository and the responsibilities of each agent team.

## Overview

The Microsoft Agent Framework workflow forms a guided software factory:

1. Planner analyzes the human request and produces a typed task list.
2. Dispatcher applies deterministic routing, deciding which specialist team should work next.
3. Implementation team fulfills tasks using role-specific agents (coder and researcher personas).
4. Verifier enforces the Reflexion loop, feeding failures back into the dispatcher until every task passes review.
5. Dispatcher aggregates completed artifacts into the final deliverable and terminates the workflow.

Shared memory lives in a `ProjectState` model stored inside `WorkflowContext` so every agent reads/writes consistent state.

## Agent Teams

### Planning Agent
- Backed by a `ChatAgent` with JSON response formatting.
- Breaks the user request into `Task` objects with assignees and descriptions.
- Seeds shared state and then signals `PLAN_CREATED` to unblock the dispatcher.

### Dispatch Team
- Pure Python executor (`DispatcherExecutor`).
- Reads shared state, emits routing signals (`DISPATCH_TASK`, `REQUEST_VERIFICATION`, `WORKFLOW_COMPLETE`).
- Ensures deterministic control flow, eliminating stochastic branching between LLM responses.

### Implementation Team
Two executors share the same structure but different instructions:
- **Coder**: produces production-ready code and applies verifier feedback.
- **Researcher**: runs investigations, summarizes findings, and unblocks the coder.

Both update task outputs and mark tasks as `needs_review` before notifying the dispatcher (`ADVANCE_TASK`).

### Verification Team
- Critic agent using JSON verdicts with `pass`/`fail`.
- On pass: marks the task `completed`.
- On fail: attaches feedback and resets the task to `pending` so the dispatcher can re-dispatch with corrective guidance.

## Control Signals

| Signal | Emitted By | Purpose |
| --- | --- | --- |
| `PLAN_CREATED` | Planner | Planner finished seeding shared state |
| `DISPATCH_TASK` | Dispatcher | Route a specific task to coder or researcher |
| `REQUEST_VERIFICATION` | Dispatcher | Ask the verifier to critique the latest output |
| `ADVANCE_TASK` | Implementers/Verifier | Notify dispatcher to re-evaluate state |
| `WORKFLOW_COMPLETE` | Dispatcher | Final artifact ready; workflow may terminate |

## Workflow Lifecycle

```text
Planner --> Dispatcher --> Implementation --> Dispatcher --> Verifier --> Dispatcher
   ^                                                                  |
   |------------------------------------------------------------------|
```

1. Human prompt enters at the planner.
2. Dispatcher loops through tasks until all are completed.
3. Each implementation iteration cycles through verification until a pass verdict.
4. Dispatcher concatenates all task outputs into `final_artifact` for downstream consumption.

This architecture ensures reliable autonomy by combining typed state, deterministic routing, and reflexive quality control.

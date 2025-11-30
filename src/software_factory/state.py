"""Typed shared state modeled with Pydantic."""

from typing import List, Literal, Optional

from agent_framework._workflows._workflow_context import WorkflowContext
from pydantic import BaseModel, Field


TaskStatus = Literal["pending", "in_progress", "needs_review", "completed", "blocked"]


class Task(BaseModel):
    """A unit of work the planner creates for downstream executors."""

    title: str = Field(..., description="Human-readable identifier for the task.")
    description: str = Field(..., description="Detailed work to be carried out.")
    assignee: Literal["coder", "researcher"] = Field(
        ..., description="Specialized implementation agent responsible for the task."
    )
    status: TaskStatus = Field("pending", description="Execution lifecycle status.")
    output: Optional[str] = Field(
        None, description="Artifact or summary produced by the implementation agent."
    )
    feedback: Optional[str] = Field(
        None, description="Verifier feedback used for iteration when a task fails review."
    )


class ProjectState(BaseModel):
    """Shared memory ledger passed between executors."""

    original_request: str = Field(
        "", description="The initial human request that kicked off the workflow."
    )
    tasks: List[Task] = Field(default_factory=list)
    current_task_index: int = 0
    final_artifact: Optional[str] = None

    def current_task(self) -> Optional[Task]:
        if 0 <= self.current_task_index < len(self.tasks):
            return self.tasks[self.current_task_index]
        return None


PROJECT_STATE_KEY = "project_shared_memory"


async def get_project_state(ctx: WorkflowContext) -> ProjectState:
    """Load the shared state, falling back to an empty ledger."""

    try:
        raw_state = await ctx.get_shared_state(PROJECT_STATE_KEY)
    except KeyError:
        state = ProjectState()
        await ctx.set_shared_state(PROJECT_STATE_KEY, state.model_dump())
        return state
    if not raw_state:
        return ProjectState()
    if isinstance(raw_state, ProjectState):
        return raw_state
    return ProjectState(**raw_state)


async def update_project_state(ctx: WorkflowContext, state: ProjectState) -> None:
    """Persist the shared state snapshot back into the workflow context."""

    await ctx.set_shared_state(PROJECT_STATE_KEY, state.model_dump())

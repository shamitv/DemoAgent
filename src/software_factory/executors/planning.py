"""Planning executor implementation."""

import json
from typing import Any, Dict, List, Literal

from agent_framework import ChatAgent, Executor, handler
from agent_framework._workflows._workflow_context import WorkflowContext
from pydantic import BaseModel

from ..client import ModelConfig, apply_model_config
from ..signals import PLAN_CREATED
from ..state import ProjectState, Task, get_project_state, update_project_state


class PlannerTaskPayload(BaseModel):
    """Structured schema returned by the planner LLM."""

    title: str
    description: str
    assignee: Literal["coder", "researcher"]


class PlannerResponsePayload(BaseModel):
    """Top-level payload that wraps the generated tasks."""

    tasks: List[PlannerTaskPayload]


class PlanningExecutor(Executor):
    """Uses an LLM to build a structured project plan."""

    def __init__(
        self,
        chat_client,
        *,
        instructions: str | None = None,
        id: str = "planner",
        model_config: ModelConfig | None = None,
    ):
        plan_instructions = instructions or (
            "You are a senior planning agent. Break software factory requests into a minimal "
            "ordered list of tasks. Each task must include: title, description, assignee "
            "(coder or researcher), and risks. NEVER return commentary outside JSON."
        )
        chat_kwargs = apply_model_config(model_config, {"temperature": 0.2})
        self.agent = ChatAgent(
            chat_client,
            instructions=plan_instructions,
            response_format=PlannerResponsePayload,
            **chat_kwargs,
        )
        super().__init__(id=id)

    @handler
    async def handle(self, message: Any, ctx: WorkflowContext) -> None:
        user_request = _message_to_text(message)
        state = await get_project_state(ctx)
        if not state.original_request:
            state.original_request = user_request

        prompt = self._build_prompt(user_request, state)
        response = await self.agent.run(prompt)
        tasks = self._parse_tasks(response)
        if not tasks:
            raise ValueError("Planner returned no tasks; ensure instructions are correct.")

        state.tasks = tasks
        state.current_task_index = 0
        await update_project_state(ctx, state)
        await ctx.send_message({"signal": PLAN_CREATED})

    def _build_prompt(self, user_request: str, state: ProjectState) -> str:
        historical = "" if not state.tasks else json.dumps([task.model_dump() for task in state.tasks])
        return (
            "Original request:\n"
            f"{user_request}\n\n"
            "Return JSON with a 'tasks' array using coder/researcher assignees."
            f" Existing tasks (if any): {historical}"
        )

    def _parse_tasks(self, response: Any) -> List[Task]:
        payload = getattr(response, "value", None)
        if isinstance(payload, PlannerResponsePayload):
            data = payload.model_dump()
        elif isinstance(payload, dict):
            data = payload
        else:
            plan_text = _response_to_text(response)
            data = json.loads(plan_text)
        raw_tasks = data.get("tasks", [])
        return [Task(**task) for task in raw_tasks]


def _message_to_text(message: Any) -> str:
    if isinstance(message, str):
        return message.strip()
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content.strip()
    if content is None and hasattr(message, "text"):
        return str(message.text)
    return str(message)


def _response_to_text(response: Any) -> str:
    if response is None:
        return ""
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text
    messages = getattr(response, "messages", None)
    if messages:
        last = messages[-1]
        if hasattr(last, "content"):
            return str(last.content)
    return str(response)

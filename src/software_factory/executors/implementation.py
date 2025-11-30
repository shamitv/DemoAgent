"""Implementation executors that perform focused work."""

from typing import Any, Dict

from agent_framework import ChatAgent, Executor, handler
from agent_framework._workflows._workflow_context import WorkflowContext

from ..client import ModelConfig, apply_model_config
from ..signals import ADVANCE_TASK, DISPATCH_TASK
from ..state import ProjectState, Task, get_project_state, update_project_state


class ImplementationExecutor(Executor):
	"""Specialized executor (coder or researcher) that performs a plan task."""

	def __init__(
		self,
		chat_client,
		role: str,
		*,
		id: str | None = None,
		model_config: ModelConfig | None = None,
	):
		self.role = role
		friendly_id = id or f"implementation_{role}"
		instructions = self._instructions_for_role(role)
		chat_kwargs = apply_model_config(model_config, {"temperature": 0.3, "top_p": 0.9})
		self.agent = ChatAgent(
			chat_client,
			instructions=instructions,
			**chat_kwargs,
		)
		super().__init__(id=friendly_id)

	@handler
	async def handle(self, message: Dict[str, Any], ctx: WorkflowContext) -> None:
		if message.get("signal") != DISPATCH_TASK:
			return
		if message.get("assignee") != self.role:
			return

		task_index = message["task_index"]
		state = await get_project_state(ctx)
		task = self._resolve_task(state, task_index)
		if task is None:
			raise IndexError(f"Task index {task_index} not found for role {self.role}.")

		prompt = self._build_prompt(state, task)
		response = await self.agent.run(prompt)
		task.output = _response_to_text(response)
		task.status = "needs_review"
		task.feedback = None
		await update_project_state(ctx, state)
		await ctx.send_message({"signal": ADVANCE_TASK, "task_index": task_index})

	def _resolve_task(self, state: ProjectState, index: int) -> Task | None:
		if 0 <= index < len(state.tasks):
			return state.tasks[index]
		return None

	def _build_prompt(self, state: ProjectState, task: Task) -> str:
		feedback = f"\nPrevious verifier feedback:\n{task.feedback}" if task.feedback else ""
		return (
			f"Original request:\n{state.original_request}\n\n"
			f"Task: {task.title}\n{task.description}\n{feedback}\n"
			"Return the complete deliverable or a concise report ready for verification."
		)

	def _instructions_for_role(self, role: str) -> str:
		if role == "researcher":
			return (
				"You are a principal researcher. Summarize findings, outline unknowns, and"
				" provide supporting evidence for the implementation agent."
			)
		return (
			"You are a senior software engineer tasked with writing production-ready code."
			" Always produce clear, well-tested deliverables and note open risks."
		)


def _response_to_text(response: Any) -> str:
	if response is None:
		return ""
	if hasattr(response, "output_text") and response.output_text:
		return response.output_text
	if hasattr(response, "messages") and response.messages:
		last = response.messages[-1]
		if hasattr(last, "content"):
			return str(last.content)
	return str(response)

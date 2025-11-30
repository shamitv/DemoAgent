"""Verification executor implementing the Reflexion loop."""

import json
from typing import Any, Dict, Literal

from agent_framework import ChatAgent, Executor, handler
from agent_framework._workflows._workflow_context import WorkflowContext
from pydantic import BaseModel

from ..client import ModelConfig, apply_model_config
from ..signals import ADVANCE_TASK, REQUEST_VERIFICATION
from ..state import ProjectState, Task, get_project_state, update_project_state


class VerificationResult(BaseModel):
	"""Structured verifier output enforced by the API."""

	verdict: Literal["pass", "fail"]
	feedback: str


class VerificationExecutor(Executor):
	"""Critic agent that approves or rejects implementation outputs."""

	def __init__(self, chat_client, *, id: str = "verifier", model_config: ModelConfig | None = None):
		instructions = (
			"You are a meticulous reviewer. Evaluate the provided implementation output"
			" against the task description. Reply in JSON with fields 'verdict'"
			" (pass/fail) and 'feedback'."
		)
		chat_kwargs = apply_model_config(model_config, {"temperature": 0})
		self.agent = ChatAgent(
			chat_client,
			instructions=instructions,
			response_format=VerificationResult,
			**chat_kwargs,
		)
		super().__init__(id=id)

	@handler
	async def handle(self, message: Dict[str, Any], ctx: WorkflowContext) -> None:
		if message.get("signal") != REQUEST_VERIFICATION:
			return

		task_index = message["task_index"]
		state = await get_project_state(ctx)
		task = self._resolve_task(state, task_index)
		if task is None:
			raise IndexError(f"Task index {task_index} missing during verification.")
		if not task.output:
			raise ValueError("Verifier invoked without implementation output.")

		prompt = self._build_prompt(state, task)
		response = await self.agent.run(prompt)
		verdict, feedback = self._parse_verdict(response)

		if verdict == "pass":
			task.status = "completed"
			task.feedback = None
		else:
			task.status = "pending"
			task.feedback = feedback or "Verifier rejected output."

		await update_project_state(ctx, state)
		await ctx.send_message({"signal": ADVANCE_TASK, "task_index": task_index})

	def _resolve_task(self, state: ProjectState, index: int) -> Task | None:
		if 0 <= index < len(state.tasks):
			return state.tasks[index]
		return None

	def _build_prompt(self, state: ProjectState, task: Task) -> str:
		return (
			f"Original request:\n{state.original_request}\n\n"
			f"Task specification:\n{task.title}\n{task.description}\n\n"
			f"Implementation output:\n{task.output}\n"
			"Respond with JSON verdict + feedback."
		)

	def _parse_verdict(self, response: Any) -> tuple[str, str]:
		payload = getattr(response, "value", None)
		if isinstance(payload, VerificationResult):
			return payload.verdict, payload.feedback
		if isinstance(payload, dict):
			return payload.get("verdict", "fail"), payload.get("feedback", "")
		text = _response_to_text(response)
		try:
			decoded = json.loads(text)
			return decoded.get("verdict", "fail"), decoded.get("feedback", "")
		except json.JSONDecodeError:
			normalized = text.lower()
			verdict = "pass" if "pass" in normalized and "fail" not in normalized else "fail"
			return verdict, text


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

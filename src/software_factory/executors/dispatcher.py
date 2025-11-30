"""Deterministic dispatcher that routes workflow control."""

from typing import Any, Dict

from agent_framework import Executor, handler
from agent_framework._workflows._workflow_context import WorkflowContext

from ..signals import (
	ADVANCE_TASK,
	DISPATCH_TASK,
	PLAN_CREATED,
	REQUEST_VERIFICATION,
	WORKFLOW_COMPLETE,
)
from ..state import ProjectState, Task, get_project_state, update_project_state


class DispatcherExecutor(Executor):
	"""Pure code routing that eliminates stochastic control flow."""

	def __init__(self, *, id: str = "dispatcher"):
		super().__init__(id=id)

	@handler
	async def handle(self, message: Dict[str, Any], ctx: WorkflowContext) -> None:
		state = await get_project_state(ctx)
		signal = (message or {}).get("signal")

		if signal not in {PLAN_CREATED, ADVANCE_TASK}:
			# Ignore unrelated noise but continue routing with current status.
			pass

		await self._route(state, ctx)

	async def _route(self, state: ProjectState, ctx: WorkflowContext) -> None:
		if not state.tasks:
			await ctx.yield_output("No tasks were planned; workflow exiting.")
			await ctx.send_message({"signal": WORKFLOW_COMPLETE})
			return

		if state.current_task_index >= len(state.tasks):
			await self._finalize(state, ctx)
			return

		task = state.current_task()
		if task is None:
			await ctx.yield_output("State pointer is out of range; stopping execution.")
			await ctx.send_message({"signal": WORKFLOW_COMPLETE})
			return

		match task.status:
			case "pending" | "blocked":
				await self._dispatch_task(ctx, state)
			case "in_progress":
				# Wait for the implementer to respond.
				return
			case "needs_review":
				await ctx.send_message(
					{"signal": REQUEST_VERIFICATION, "task_index": state.current_task_index}
				)
			case "completed":
				state.current_task_index += 1
				await update_project_state(ctx, state)
				await self._route(state, ctx)
			case _:
				await ctx.yield_output(
					f"Unknown task status '{task.status}'. Manual intervention required."
				)

	async def _dispatch_task(self, ctx: WorkflowContext, state: ProjectState) -> None:
		task = state.current_task()
		if not task:
			return
		task.status = "in_progress"
		await update_project_state(ctx, state)
		await ctx.send_message(
			{
				"signal": DISPATCH_TASK,
				"task_index": state.current_task_index,
				"assignee": task.assignee,
			}
		)

	async def _finalize(self, state: ProjectState, ctx: WorkflowContext) -> None:
		if not state.final_artifact:
			outputs = [task.output for task in state.tasks if task.output]
			state.final_artifact = "\n\n".join(outputs) if outputs else "Workflow completed."
			await update_project_state(ctx, state)
		await ctx.yield_output(state.final_artifact or "Workflow completed.")
		await ctx.send_message({"signal": WORKFLOW_COMPLETE})

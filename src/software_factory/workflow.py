"""Workflow assembly for the Microsoft Agent Framework software factory."""

from __future__ import annotations

from typing import Any, Callable, Dict

from agent_framework import WorkflowBuilder

from .executors.dispatcher import DispatcherExecutor
from .executors.implementation import ImplementationExecutor
from .executors.planning import PlanningExecutor
from .executors.verification import VerificationExecutor
from .signals import DISPATCH_TASK, REQUEST_VERIFICATION


def build_workflow(chat_client) -> Any:
	"""Construct the Planner -> Dispatcher -> Implementers -> Verifier workflow."""

	planner = PlanningExecutor(chat_client)
	dispatcher = DispatcherExecutor()
	coder = ImplementationExecutor(chat_client, role="coder")
	researcher = ImplementationExecutor(chat_client, role="researcher")
	verifier = VerificationExecutor(chat_client)

	builder = WorkflowBuilder(name="software_factory")
	builder.set_start_executor(planner)
	builder.add_edge(planner, dispatcher)
	builder.add_edge(dispatcher, coder, condition=_assignee_condition("coder"))
	builder.add_edge(dispatcher, researcher, condition=_assignee_condition("researcher"))
	builder.add_edge(dispatcher, verifier, condition=_verification_condition)
	builder.add_edge(coder, dispatcher)
	builder.add_edge(researcher, dispatcher)
	builder.add_edge(verifier, dispatcher)

	return builder.build()


def _assignee_condition(target: str) -> Callable[[Dict[str, Any]], bool]:
	def _condition(message: Dict[str, Any]) -> bool:
		return (
			isinstance(message, dict)
			and message.get("signal") == DISPATCH_TASK
			and message.get("assignee") == target
		)

	return _condition


def _verification_condition(message: Dict[str, Any]) -> bool:
	return isinstance(message, dict) and message.get("signal") == REQUEST_VERIFICATION

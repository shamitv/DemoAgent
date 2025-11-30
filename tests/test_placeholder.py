"""Dispatcher-focused tests exercising shared-state routing."""

import asyncio

from software_factory.executors.dispatcher import DispatcherExecutor
from software_factory.signals import (
    ADVANCE_TASK,
    DISPATCH_TASK,
    PLAN_CREATED,
    WORKFLOW_COMPLETE,
)
from software_factory.state import ProjectState, Task


class _FakeContext:
    def __init__(self, state: ProjectState):
        self._shared_state = state.model_dump()
        self.sent_messages = []
        self.outputs = []

    async def get_shared_state(self, _key: str):
        return self._shared_state

    async def set_shared_state(self, _key: str, value):
        self._shared_state = value

    async def send_message(self, payload):
        self.sent_messages.append(payload)

    async def yield_output(self, output):
        self.outputs.append(output)


def test_dispatcher_routes_pending_task() -> None:
    state = ProjectState(
        original_request="Ship feature",
        tasks=[Task(title="Implement", description="Write code", assignee="coder")],
    )
    dispatcher = DispatcherExecutor()
    ctx = _FakeContext(state)

    asyncio.run(dispatcher.handle({"signal": PLAN_CREATED}, ctx))

    assert ctx.sent_messages, "Dispatcher did not emit a dispatch message."
    dispatch = ctx.sent_messages[-1]
    assert dispatch["signal"] == DISPATCH_TASK
    assert dispatch["assignee"] == "coder"


def test_dispatcher_finalizes_workflow() -> None:
    state = ProjectState(
        original_request="Ship feature",
        tasks=[
            Task(
                title="Implement",
                description="Write code",
                assignee="coder",
                status="completed",
                output="result",
            )
        ],
        current_task_index=1,
    )
    dispatcher = DispatcherExecutor()
    ctx = _FakeContext(state)

    asyncio.run(dispatcher.handle({"signal": ADVANCE_TASK}, ctx))

    assert ctx.outputs, "Dispatcher did not emit a final artifact."
    assert ctx.sent_messages[-1]["signal"] == WORKFLOW_COMPLETE

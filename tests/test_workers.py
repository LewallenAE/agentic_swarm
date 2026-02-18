"""Tests for the stub worker agents."""
from __future__ import annotations

import asyncio

import pytest

from agentic_swarm.communication import MessageBus, create_message
from agentic_swarm.controller import Task
from agentic_swarm.workers import CoderAgent, PlannerAgent, ReviewerAgent


def _make_task(description: str = "test task", request_id: str = "req-1") -> Task:
    return Task(
        id="task-1",
        description=description,
        task_type="test",
        request_id=request_id,
    )


@pytest.mark.asyncio
async def test_planner_returns_subtasks() -> None:
    bus = MessageBus()
    controller_inbox = bus.register_agent("controller")
    planner = PlannerAgent(name="planner", bus=bus)

    task = _make_task("build a calculator")
    msg = create_message("controller", "planner", "task_assign", task)
    await planner.inbox.put(msg)

    await planner.handle_message(msg)

    result = await asyncio.wait_for(controller_inbox.get(), timeout=0.5)
    assert result.type == "task_result"
    assert result.payload["result_type"] == "plan"
    assert isinstance(result.payload["subtasks"], list)
    assert len(result.payload["subtasks"]) > 0
    assert result.payload["request_id"] == "req-1"


@pytest.mark.asyncio
async def test_coder_returns_code() -> None:
    bus = MessageBus()
    controller_inbox = bus.register_agent("controller")
    coder = CoderAgent(name="coder", bus=bus)

    task = _make_task("implement calculator")
    msg = create_message("controller", "coder", "task_assign", task)
    await coder.inbox.put(msg)

    await coder.handle_message(msg)

    result = await asyncio.wait_for(controller_inbox.get(), timeout=0.5)
    assert result.type == "task_result"
    assert result.payload["result_type"] == "code"
    assert "code" in result.payload
    assert result.payload["request_id"] == "req-1"


@pytest.mark.asyncio
async def test_reviewer_returns_lgtm() -> None:
    bus = MessageBus()
    controller_inbox = bus.register_agent("controller")
    reviewer = ReviewerAgent(name="reviewer", bus=bus)

    task = _make_task("review calculator code")
    msg = create_message("controller", "reviewer", "task_assign", task)
    await reviewer.inbox.put(msg)

    await reviewer.handle_message(msg)

    result = await asyncio.wait_for(controller_inbox.get(), timeout=0.5)
    assert result.type == "task_result"
    assert result.payload["result_type"] == "review"
    assert result.payload["verdict"] == "LGTM"
    assert result.payload["request_id"] == "req-1"


@pytest.mark.asyncio
async def test_workers_ignore_non_task_assign() -> None:
    """Workers should pass through non-task_assign messages to super()."""
    bus = MessageBus()
    bus.register_agent("controller")
    planner = PlannerAgent(name="planner", bus=bus)

    msg = create_message("someone", "planner", "random_type", None)
    # Should not raise
    await planner.handle_message(msg)

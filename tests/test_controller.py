"""Tests for the Controller agent."""
from __future__ import annotations

import asyncio

import pytest

from agentic_swarm.communication import MessageBus, create_message
from agentic_swarm.controller import Controller


@pytest.mark.asyncio
async def test_controller_assign_task_sends_message() -> None:
    bus = MessageBus()
    worker_inbox = bus.register_agent("worker")
    controller = Controller(name="controller", role="controller", bus=bus)

    task = controller.create_task("do work", {"x": 1})
    await controller.assign_task(task.id, "worker")

    assert task.status == "assigned"
    assert task.assignee == "worker"

    msg = await asyncio.wait_for(worker_inbox.get(), timeout=0.1)
    assert msg.type == "task_assign"
    assert msg.payload.id == task.id


@pytest.mark.asyncio
async def test_pipeline_user_request_to_plan() -> None:
    """user_request → controller creates plan task and assigns to planner."""
    bus = MessageBus()
    planner_inbox = bus.register_agent("planner")
    user_inbox = bus.register_agent("user")
    controller = Controller(name="controller", role="controller", bus=bus)

    request = create_message("user", "controller", "user_request", "build a calculator")
    await controller.handle_message(request)

    # User should get a "Planning..." status message
    user_msg = await asyncio.wait_for(user_inbox.get(), timeout=0.5)
    assert user_msg.type == "user_output"
    assert "Planning" in user_msg.payload["text"]

    # Planner should get a task_assign
    planner_msg = await asyncio.wait_for(planner_inbox.get(), timeout=0.5)
    assert planner_msg.type == "task_assign"
    assert planner_msg.payload.task_type == "plan"


@pytest.mark.asyncio
async def test_pipeline_plan_to_code_to_review_to_done() -> None:
    """Full pipeline: user_request → plan → code → review → final user_output."""
    bus = MessageBus()
    planner_inbox = bus.register_agent("planner")
    coder_inbox = bus.register_agent("coder")
    reviewer_inbox = bus.register_agent("reviewer")
    user_inbox = bus.register_agent("user")
    controller = Controller(name="controller", role="controller", bus=bus)

    # 1. Send user_request
    request = create_message("user", "controller", "user_request", "build X")
    await controller.handle_message(request)

    # Drain user "Planning..." + planner task_assign
    await asyncio.wait_for(user_inbox.get(), timeout=0.5)
    planner_msg = await asyncio.wait_for(planner_inbox.get(), timeout=0.5)
    task_obj = planner_msg.payload
    request_id = task_obj.request_id

    # 2. Planner returns subtasks
    plan_result = create_message("planner", "controller", "task_result", {
        "task_id": task_obj.id,
        "request_id": request_id,
        "result_type": "plan",
        "subtasks": ["Implement core", "Write tests"],
    })
    await controller.handle_message(plan_result)

    # User gets "Plan ready" message
    plan_msg = await asyncio.wait_for(user_inbox.get(), timeout=0.5)
    assert "2 coding task(s)" in plan_msg.payload["text"]

    # Coder gets 2 task_assign messages
    code_task_1 = await asyncio.wait_for(coder_inbox.get(), timeout=0.5)
    code_task_2 = await asyncio.wait_for(coder_inbox.get(), timeout=0.5)

    # 3. Coder returns results
    for ct in [code_task_1, code_task_2]:
        code_result = create_message("coder", "controller", "task_result", {
            "task_id": ct.payload.id,
            "request_id": request_id,
            "result_type": "code",
            "description": ct.payload.description,
            "code": "print('hello')",
        })
        await controller.handle_message(code_result)

    # User gets 2 "Completed" messages
    await asyncio.wait_for(user_inbox.get(), timeout=0.5)
    await asyncio.wait_for(user_inbox.get(), timeout=0.5)

    # Reviewer gets task_assign
    reviewer_msg = await asyncio.wait_for(reviewer_inbox.get(), timeout=0.5)
    assert reviewer_msg.payload.task_type == "review"

    # 4. Reviewer returns LGTM
    review_result = create_message("reviewer", "controller", "task_result", {
        "task_id": reviewer_msg.payload.id,
        "request_id": request_id,
        "result_type": "review",
        "description": "review",
        "verdict": "LGTM",
    })
    await controller.handle_message(review_result)

    # User gets final message
    final_msg = await asyncio.wait_for(user_inbox.get(), timeout=0.5)
    assert final_msg.payload["final"] is True
    assert "LGTM" in final_msg.payload["text"]

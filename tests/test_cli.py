"""Tests for the UserAgent and CLI."""
from __future__ import annotations

import asyncio

import pytest

from agentic_swarm.cli import UserAgent
from agentic_swarm.communication import MessageBus, create_message


@pytest.mark.asyncio
async def test_user_agent_registers_on_bus() -> None:
    bus = MessageBus()
    user = UserAgent(name="user", bus=bus)
    assert "user" in bus._queues
    assert user.role == "user"


@pytest.mark.asyncio
async def test_drain_inbox_collects_user_output() -> None:
    bus = MessageBus()
    user = UserAgent(name="user", bus=bus)

    msg1 = create_message("controller", "user", "user_output", {"text": "hello", "final": False})
    msg2 = create_message("controller", "user", "user_output", {"text": "done", "final": True})
    await user.inbox.put(msg1)
    await user.inbox.put(msg2)

    results = await user._drain_inbox()
    assert len(results) == 2
    assert results[0]["text"] == "hello"
    assert results[1]["text"] == "done"


@pytest.mark.asyncio
async def test_drain_inbox_stops_on_shutdown() -> None:
    bus = MessageBus()
    user = UserAgent(name="user", bus=bus)
    user._running = True

    msg = create_message("swarm", "user", "shutdown", None)
    await user.inbox.put(msg)

    await user._drain_inbox()
    assert user._running is False


@pytest.mark.asyncio
async def test_wait_for_results_receives_final(capsys: pytest.CaptureFixture[str]) -> None:
    bus = MessageBus()
    user = UserAgent(name="user", bus=bus)
    user._running = True

    async def feed_messages() -> None:
        await asyncio.sleep(0.05)
        msg = create_message(
            "controller", "user", "user_output",
            {"text": "[reviewer] Review complete: LGTM.", "final": True},
        )
        await user.inbox.put(msg)

    asyncio.get_running_loop().create_task(feed_messages())
    await user._wait_for_results(timeout=2.0)

    captured = capsys.readouterr()
    assert "LGTM" in captured.out


@pytest.mark.asyncio
async def test_wait_for_results_times_out(capsys: pytest.CaptureFixture[str]) -> None:
    bus = MessageBus()
    user = UserAgent(name="user", bus=bus)
    user._running = True

    await user._wait_for_results(timeout=0.5)

    captured = capsys.readouterr()
    assert "timed out" in captured.out

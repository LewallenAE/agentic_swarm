"""Tests for inter-agent communication."""
from __future__ import annotations

import asyncio

import pytest

from agentic_swarm.communication import MessageBus, create_message


@pytest.mark.asyncio
async def test_message_bus_direct_and_broadcast() -> None:
    bus = MessageBus()
    inbox_a = bus.register_agent("a")
    inbox_b = bus.register_agent("b")

    await bus.send(create_message("a", "b", "ping", {"value": 1}))
    msg_b = await asyncio.wait_for(inbox_b.get(), timeout=0.1)
    assert msg_b.type == "ping"
    assert msg_b.payload == {"value": 1}

    await bus.send(create_message("a", None, "broadcast", None))
    msg_a = await asyncio.wait_for(inbox_a.get(), timeout=0.1)
    msg_b2 = await asyncio.wait_for(inbox_b.get(), timeout=0.1)
    assert msg_a.type == "broadcast"
    assert msg_b2.type == "broadcast"

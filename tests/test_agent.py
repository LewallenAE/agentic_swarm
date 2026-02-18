"""Tests for the base Agent class."""
from __future__ import annotations

import asyncio

import pytest

from agentic_swarm.agent import Agent
from agentic_swarm.communication import MessageBus


class NoopAgent(Agent):
    async def handle_message(self, message) -> None:  # pragma: no cover - simple stub
        return


@pytest.mark.asyncio
async def test_agent_send_and_broadcast() -> None:
    bus = MessageBus()
    sender = NoopAgent(name="sender", role="tester", bus=bus)
    receiver_inbox = bus.register_agent("receiver")

    await sender.send("receiver", "ping", {"ok": True})
    msg = await asyncio.wait_for(receiver_inbox.get(), timeout=0.1)
    assert msg.sender == "sender"
    assert msg.type == "ping"
    assert msg.payload == {"ok": True}

    await sender.broadcast("notice", None)
    msg_receiver = await asyncio.wait_for(receiver_inbox.get(), timeout=0.1)
    msg_sender = await asyncio.wait_for(sender.inbox.get(), timeout=0.1)
    assert msg_receiver.type == "notice"
    assert msg_sender.type == "notice"

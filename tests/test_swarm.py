"""Tests for the Swarm manager."""
from __future__ import annotations

import asyncio

import pytest

from agentic_swarm.agent import Agent
from agentic_swarm.communication import MessageBus
from agentic_swarm.swarm import Swarm


class ShutdownAgent(Agent):
    async def run(self) -> None:
        await asyncio.sleep(0)
        await self.request_shutdown()
        await super().run()


@pytest.mark.asyncio
async def test_swarm_stops_on_broadcast() -> None:
    bus = MessageBus()
    agent = ShutdownAgent(name="agent", role="tester", bus=bus)
    swarm = Swarm(agents=[agent], bus=bus)

    await asyncio.wait_for(swarm.run(), timeout=0.5)

"""Swarm manager - spawns agents, manages lifecycle, runs execution loop."""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Iterable

from .agent import Agent
from .communication import Message, MessageBus, create_message


class Swarm:
    """Coordinates agent lifecycles and execution."""

    def __init__(self, agents: Iterable[Agent], bus: MessageBus | None = None) -> None:
        self.agents: list[Agent] = list(agents)
        if not self.agents:
            raise ValueError("swarm requires at least one agent")

        if bus is None:
            bus = self.agents[0].bus
        self.bus = bus

        for agent in self.agents:
            if agent.bus is not self.bus:
                raise ValueError("all agents must share the same MessageBus")

        self.logger = logging.getLogger("agentic_swarm.swarm")
        self._stop_event = asyncio.Event()
        self._observer_name = f"_swarm_observer_{uuid.uuid4().hex}"
        self._observer_queue: asyncio.Queue[Message] = self.bus.register_agent(self._observer_name)

    async def run(self, duration: float | None = None) -> None:
        """Start all agents and run until stopped or duration elapses."""
        async with asyncio.TaskGroup() as task_group:
            for agent in self.agents:
                task_group.create_task(agent.run())

            task_group.create_task(self._watch_for_shutdown())

            if duration is None:
                await self._stop_event.wait()
            else:
                await asyncio.sleep(duration)
                await self.stop()

    async def stop(self) -> None:
        """Request shutdown for all agents."""
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        message = create_message(
            sender="swarm",
            recipient=None,
            message_type="shutdown",
            payload=None,
        )
        await self.bus.send(message)

    async def _watch_for_shutdown(self) -> None:
        while not self._stop_event.is_set():
            message = await self._observer_queue.get()
            if message.type == "shutdown":
                self._stop_event.set()
                break

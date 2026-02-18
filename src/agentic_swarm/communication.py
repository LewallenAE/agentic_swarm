"""Inter-agent messaging - message bus and shared state for the swarm."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Message:
    """Immutable message payload passed between agents."""

    id: str
    sender: str
    recipient: str | None
    type: str
    payload: Any
    timestamp: float


def create_message(
    sender: str,
    recipient: str | None,
    message_type: str,
    payload: Any | None = None,
) -> Message:
    """Create a new message with a unique id and timestamp."""
    return Message(
        id=str(uuid.uuid4()),
        sender=sender,
        recipient=recipient,
        type=message_type,
        payload=payload,
        timestamp=time.time(),
    )


class MessageBus:
    """Simple in-memory message bus for agent communication."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[Message]] = {}
        self.logger = logging.getLogger("agentic_swarm.bus")

    def register_agent(self, name: str) -> asyncio.Queue[Message]:
        """Register an agent and return its inbox queue."""
        if name in self._queues:
            raise ValueError(f"agent already registered: {name}")
        queue: asyncio.Queue[Message] = asyncio.Queue()
        self._queues[name] = queue
        self.logger.info("agent registered: %s", name)
        return queue

    async def send(self, message: Message) -> None:
        """Send a message to a recipient or broadcast if recipient is None."""
        if message.recipient is None:
            await self._broadcast(message)
            return
        queue = self._queues.get(message.recipient)
        if queue is None:
            self.logger.warning("recipient not found: %s", message.recipient)
            return
        await queue.put(message)

    async def _broadcast(self, message: Message) -> None:
        if not self._queues:
            return
        for queue in self._queues.values():
            await queue.put(message)


class SharedState:
    """Async-safe shared state for agents."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str, default: Any | None = None) -> Any:
        async with self._lock:
            return self._data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._data[key] = value

    async def update(self, values: dict[str, Any]) -> None:
        async with self._lock:
            self._data.update(values)

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return dict(self._data)

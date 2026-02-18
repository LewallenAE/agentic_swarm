"""Base Agent class - all swarm agents inherit from this."""
from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from .communication import Message, MessageBus, create_message


class MessageHandlingError(Exception):
    """Raised when an agent fails to process a message."""


class Agent:
    """Base class for all agents in the swarm."""

    def __init__(
        self,
        name: str,
        role: str,
        bus: MessageBus,
        capabilities: Iterable[str] | None = None,
    ) -> None:
        self.name = name
        self.role = role
        self.capabilities = set(capabilities or [])
        self.bus = bus
        self.inbox = bus.register_agent(name)
        self.logger = logging.getLogger(f"agentic_swarm.agent.{name}")
        self._running = False

    async def run(self) -> None:
        """Main agent loop. Processes inbound messages until shutdown."""
        self._running = True
        self.logger.info("agent started")
        while self._running:
            message = await self.inbox.get()
            if message.type == "shutdown":
                self.logger.info("shutdown received")
                self._running = False
                break
            try:
                await self.handle_message(message)
            except MessageHandlingError:
                self.logger.exception("error handling message: %s", message)
            except (KeyError, ValueError, TypeError, AttributeError) as exc:
                self.logger.exception(
                    "unexpected %s handling message: %s", type(exc).__name__, message
                )
        self.logger.info("agent stopped")

    async def handle_message(self, message: Message) -> None:
        """Handle a single message. Override in subclasses."""
        self.logger.info("message received: %s", message.type)

    async def send(self, recipient: str, message_type: str, payload: Any | None = None) -> None:
        """Send a direct message to another agent."""
        message = create_message(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
        )
        await self.bus.send(message)

    async def broadcast(self, message_type: str, payload: Any | None = None) -> None:
        """Broadcast a message to all agents."""
        message = create_message(
            sender=self.name,
            recipient=None,
            message_type=message_type,
            payload=payload,
        )
        await self.bus.send(message)

    async def request_shutdown(self) -> None:
        """Request a swarm-wide shutdown."""
        await self.broadcast("shutdown")

"""Interactive CLI — UserAgent with REPL loop."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .agent import Agent
from .communication import Message, MessageBus

BANNER = """\
==================================================
  Agentic Swarm - Interactive CLI
  Type a request and the swarm will collaborate.
  Commands: quit, exit, status
==================================================
"""

PROMPT = "\nswarm> "


class UserAgent(Agent):
    """Agent that bridges the human user and the swarm via an interactive REPL."""

    def __init__(self, name: str, bus: MessageBus) -> None:
        super().__init__(name=name, role="user", bus=bus)
        self.logger = logging.getLogger("agentic_swarm.user")
        self._output_lines: list[str] = []

    async def run(self) -> None:
        """Interactive REPL: read user input, send to controller, print results."""
        self._running = True
        self.logger.info("user agent started")
        print(BANNER)

        loop = asyncio.get_running_loop()

        while self._running:
            try:
                line = await loop.run_in_executor(None, self._read_input)
            except (EOFError, KeyboardInterrupt):
                break

            if line is None:
                break

            stripped = line.strip()
            if not stripped:
                continue

            if stripped.lower() in ("quit", "exit"):
                print("Shutting down swarm...")
                await self.request_shutdown()
                break

            if stripped.lower() == "status":
                print("  Swarm is running. Agents are listening.")
                continue

            await self.send("controller", "user_request", stripped)
            print("  -> Request sent to swarm.\n")

            await self._wait_for_results(timeout=30.0)

        self.logger.info("user agent stopped")

    def _read_input(self) -> str | None:
        """Blocking stdin read, called via run_in_executor."""
        try:
            return input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            return None

    async def _drain_inbox(self) -> list[dict[str, Any]]:
        """Pull all available user_output messages from inbox without blocking."""
        messages: list[dict[str, Any]] = []
        while True:
            try:
                msg: Message = self.inbox.get_nowait()
            except asyncio.QueueEmpty:
                break
            if msg.type == "shutdown":
                self._running = False
                break
            if msg.type == "user_output" and isinstance(msg.payload, dict):
                messages.append(msg.payload)
        return messages

    async def _wait_for_results(self, timeout: float = 30.0) -> None:
        """Block until a final=True message arrives or timeout elapses."""
        deadline = asyncio.get_running_loop().time() + timeout
        while self._running:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                print("  (timed out waiting for response)")
                break
            try:
                msg: Message = await asyncio.wait_for(
                    self.inbox.get(), timeout=min(remaining, 1.0)
                )
            except TimeoutError:
                continue

            if msg.type == "shutdown":
                self._running = False
                break

            if msg.type == "user_output" and isinstance(msg.payload, dict):
                text = msg.payload.get("text", "")
                print(f"  {text}")
                if msg.payload.get("final", False):
                    break

    async def handle_message(self, message: Message) -> None:
        """Not used in REPL mode — messages are consumed by _wait_for_results."""
        self.logger.debug("handle_message called: %s", message.type)

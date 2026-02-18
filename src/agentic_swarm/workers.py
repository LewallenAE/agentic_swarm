"""Stub worker agents — planner, coder, reviewer."""
from __future__ import annotations

import logging

from .agent import Agent
from .communication import Message, MessageBus


class PlannerAgent(Agent):
    """Receives a user request and returns a list of subtasks."""

    def __init__(self, name: str, bus: MessageBus) -> None:
        super().__init__(name=name, role="planner", bus=bus, capabilities=["planning"])
        self.logger = logging.getLogger(f"agentic_swarm.planner.{name}")

    async def handle_message(self, message: Message) -> None:
        if message.type != "task_assign":
            await super().handle_message(message)
            return

        task = message.payload
        description: str = task.description if hasattr(task, "description") else str(task)
        self.logger.info("planning: %s", description)

        subtasks = [
            "Implement core logic",
            "Write tests",
        ]

        await self.send(
            "controller",
            "task_result",
            {
                "task_id": task.id if hasattr(task, "id") else None,
                "request_id": task.request_id if hasattr(task, "request_id") else None,
                "result_type": "plan",
                "subtasks": subtasks,
            },
        )


class CoderAgent(Agent):
    """Receives a coding subtask and returns placeholder code."""

    def __init__(self, name: str, bus: MessageBus) -> None:
        super().__init__(name=name, role="coder", bus=bus, capabilities=["coding"])
        self.logger = logging.getLogger(f"agentic_swarm.coder.{name}")

    async def handle_message(self, message: Message) -> None:
        if message.type != "task_assign":
            await super().handle_message(message)
            return

        task = message.payload
        description: str = task.description if hasattr(task, "description") else str(task)
        self.logger.info("coding: %s", description)

        code = f"# Stub implementation for: {description}\nprint('Hello from {description}')\n"

        await self.send(
            "controller",
            "task_result",
            {
                "task_id": task.id if hasattr(task, "id") else None,
                "request_id": task.request_id if hasattr(task, "request_id") else None,
                "result_type": "code",
                "description": description,
                "code": code,
            },
        )


class ReviewerAgent(Agent):
    """Receives code and returns a review."""

    def __init__(self, name: str, bus: MessageBus) -> None:
        super().__init__(name=name, role="reviewer", bus=bus, capabilities=["review"])
        self.logger = logging.getLogger(f"agentic_swarm.reviewer.{name}")

    async def handle_message(self, message: Message) -> None:
        if message.type != "task_assign":
            await super().handle_message(message)
            return

        task = message.payload
        description: str = task.description if hasattr(task, "description") else str(task)
        self.logger.info("reviewing: %s", description)

        await self.send(
            "controller",
            "task_result",
            {
                "task_id": task.id if hasattr(task, "id") else None,
                "request_id": task.request_id if hasattr(task, "request_id") else None,
                "result_type": "review",
                "description": description,
                "verdict": "LGTM",
            },
        )

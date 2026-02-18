"""Controller agent - routes tasks and orchestrates the swarm."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from .agent import Agent
from .communication import Message, MessageBus


@dataclass
class Task:
    """Unit of work tracked by the controller."""

    id: str
    description: str
    payload: Any | None = None
    status: str = "pending"
    assignee: str | None = None
    task_type: str = "generic"
    request_id: str | None = None


@dataclass
class RequestState:
    """Tracks the lifecycle of a single user request through the pipeline."""

    request_id: str
    user_agent: str
    description: str
    pending_subtasks: int = 0
    coded_items: list[dict[str, Any]] = field(default_factory=list)
    phase: str = "planning"


class Controller(Agent):
    """Controller agent responsible for task routing and pipeline orchestration."""

    def __init__(
        self,
        name: str,
        role: str,
        bus: MessageBus,
        capabilities: list[str] | None = None,
    ) -> None:
        super().__init__(name=name, role=role, bus=bus, capabilities=capabilities)
        self._tasks: dict[str, Task] = {}
        self._requests: dict[str, RequestState] = {}
        self.logger = logging.getLogger("agentic_swarm.controller")

    def create_task(
        self,
        description: str,
        payload: Any | None = None,
        task_type: str = "generic",
        request_id: str | None = None,
    ) -> Task:
        task = Task(
            id=str(uuid.uuid4()),
            description=description,
            payload=payload,
            task_type=task_type,
            request_id=request_id,
        )
        self._tasks[task.id] = task
        self.logger.info("task created: %s (%s)", task.id, task_type)
        return task

    async def assign_task(self, task_id: str, agent_name: str) -> None:
        task = self._tasks.get(task_id)
        if task is None:
            self.logger.warning("task not found: %s", task_id)
            return
        task.status = "assigned"
        task.assignee = agent_name
        await self.send(agent_name, "task_assign", task)
        self.logger.info("task assigned: %s -> %s", task_id, agent_name)

    async def handle_message(self, message: Message) -> None:
        if message.type == "user_request":
            await self._handle_user_request(message)
            return
        if message.type == "task_result" and isinstance(message.payload, dict):
            await self._handle_task_result(message)
            return
        if message.type == "task_request":
            for task in self._tasks.values():
                if task.status == "pending":
                    await self.assign_task(task.id, message.sender)
                    return
            self.logger.info("no pending tasks for %s", message.sender)
            return
        await super().handle_message(message)

    async def _handle_user_request(self, message: Message) -> None:
        """Start the pipeline: create a planning task and assign to planner."""
        description = message.payload if isinstance(message.payload, str) else str(message.payload)
        request_id = str(uuid.uuid4())

        req = RequestState(
            request_id=request_id,
            user_agent=message.sender,
            description=description,
        )
        self._requests[request_id] = req

        await self.send(
            req.user_agent,
            "user_output",
            {"text": "[controller] Received request. Planning...", "final": False},
        )

        task = self.create_task(
            description=description,
            task_type="plan",
            request_id=request_id,
        )
        await self.assign_task(task.id, "planner")

    async def _handle_task_result(self, message: Message) -> None:
        """Route results through the pipeline: plan → code → review → done."""
        payload = message.payload
        task_id: str | None = payload.get("task_id")
        request_id: str | None = payload.get("request_id")
        result_type: str = payload.get("result_type", "")

        if task_id is not None:
            task = self._tasks.get(task_id)
            if task is not None:
                task.status = "complete"

        if request_id is None:
            return
        req = self._requests.get(request_id)
        if req is None:
            return

        if result_type == "plan":
            await self._on_plan_complete(req, payload)
        elif result_type == "code":
            await self._on_code_complete(req, payload)
        elif result_type == "review":
            await self._on_review_complete(req, payload)

    async def _on_plan_complete(self, req: RequestState, payload: dict[str, Any]) -> None:
        subtasks: list[str] = payload.get("subtasks", [])
        req.phase = "coding"
        req.pending_subtasks = len(subtasks)

        await self.send(
            req.user_agent,
            "user_output",
            {
                "text": f"[controller] Plan ready. {len(subtasks)} coding task(s) dispatched.",
                "final": False,
            },
        )

        for desc in subtasks:
            task = self.create_task(
                description=desc,
                task_type="code",
                request_id=req.request_id,
            )
            await self.assign_task(task.id, "coder")

    async def _on_code_complete(self, req: RequestState, payload: dict[str, Any]) -> None:
        description = payload.get("description", "")
        req.coded_items.append(payload)
        req.pending_subtasks -= 1

        await self.send(
            req.user_agent,
            "user_output",
            {
                "text": f"[coder] Completed: {description}. Sending to review...",
                "final": False,
            },
        )

        if req.pending_subtasks <= 0:
            req.phase = "review"
            task = self.create_task(
                description=f"Review code for: {req.description}",
                payload={"coded_items": req.coded_items},
                task_type="review",
                request_id=req.request_id,
            )
            await self.assign_task(task.id, "reviewer")

    async def _on_review_complete(self, req: RequestState, payload: dict[str, Any]) -> None:
        verdict = payload.get("verdict", "done")
        req.phase = "done"

        await self.send(
            req.user_agent,
            "user_output",
            {
                "text": f"[reviewer] Review complete: {verdict}.",
                "final": True,
            },
        )

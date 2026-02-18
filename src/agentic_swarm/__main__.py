"""Entry point for running the agentic swarm: python -m agentic_swarm."""
from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from .cli import UserAgent
from .communication import MessageBus
from .config import load_config
from .controller import Controller
from .swarm import Swarm
from .workers import CoderAgent, PlannerAgent, ReviewerAgent


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def _async_main(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level)

    config: dict[str, Any] = load_config(args.config) if args.config else {}
    logging.getLogger("agentic_swarm").info("loaded config keys: %s", list(config.keys()))

    bus = MessageBus()

    controller = Controller(name="controller", role="controller", bus=bus)
    planner = PlannerAgent(name="planner", bus=bus)
    coder = CoderAgent(name="coder", bus=bus)
    reviewer = ReviewerAgent(name="reviewer", bus=bus)
    user = UserAgent(name="user", bus=bus)

    agents = [controller, planner, coder, reviewer, user]
    swarm = Swarm(agents=agents, bus=bus)

    try:
        if args.batch:
            await swarm.run(duration=args.duration or 5.0)
        else:
            await swarm.run()
    finally:
        await swarm.stop()

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the agentic swarm")
    parser.add_argument("--config", type=str, default=None, help="Path to YAML config")
    parser.add_argument("--duration", type=float, default=None, help="Run duration in seconds")
    parser.add_argument(
        "--log-level", type=str, default="WARNING", help="Logging level (default: WARNING)"
    )
    parser.add_argument(
        "--batch", action="store_true", help="Run in non-interactive batch mode"
    )
    args = parser.parse_args(argv)

    try:
        return asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

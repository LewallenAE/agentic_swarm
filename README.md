# Agentic Swarm

A pure-Python autonomous multi-agent orchestration framework built from scratch. No external AI/agent frameworks — just `asyncio`, structured messaging, and cooperative agents that collaborate to fulfill complex requests.

## Overview

Agentic Swarm is a ground-up implementation of a multi-agent system where specialized agents communicate through an asynchronous message bus to plan, execute, and review work. Users interact with the swarm through an interactive REPL — type a request, and the agents autonomously decompose it into subtasks, generate code, and review the results.

### Key Principles

- **Zero framework dependencies** — no LangChain, AutoGen, CrewAI, or OpenAI Swarm
- **Pure async** — built on `asyncio.TaskGroup` for true concurrent agent execution
- **Message-driven** — all agent coordination happens through an in-memory message bus
- **Extensible** — swap stub agents for LLM-backed implementations without changing the orchestration layer

## Quick Start

### Requirements

- Python 3.11+

### Installation

```bash
# Clone the repository
git clone https://github.com/LewallenAE/agentic_swarm.git
cd agentic_swarm

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Running the REPL

```bash
python -m agentic_swarm
```

This launches the interactive CLI. Type any request and the swarm will collaborate to fulfill it:

```
==================================================
  Agentic Swarm - Interactive CLI
  Type a request and the swarm will collaborate.
  Commands: quit, exit, status
==================================================

swarm> build me a calculator
  -> Request sent to swarm.

  [controller] Received request. Planning...
  [controller] Plan ready. 2 coding task(s) dispatched.
  [coder] Completed: Implement core logic. Sending to review...
  [coder] Completed: Write tests. Sending to review...
  [reviewer] Review complete: LGTM.

swarm> quit
Shutting down swarm...
```

### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--log-level` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `WARNING` |
| `--config` | Path to a YAML configuration file | None |
| `--batch` | Run in non-interactive batch mode | Off |
| `--duration` | Run duration in seconds (batch mode) | `5.0` |

```bash
# Verbose logging to see agent internals
python -m agentic_swarm --log-level DEBUG

# Batch mode for scripting
python -m agentic_swarm --batch --duration 10
```

## Architecture

### Agent Pipeline

Every user request flows through a four-stage pipeline:

```
User Input
  │
  ▼
UserAgent ──user_request──► Controller
                               │
                               ▼
                          PlannerAgent    (1. Decompose into subtasks)
                               │
                               ▼
                          CoderAgent      (2. Implement each subtask)
                               │
                               ▼
                          ReviewerAgent   (3. Review the combined output)
                               │
                               ▼
Controller ──user_output──► UserAgent     (4. Display results to user)
```

### Core Components

```
src/agentic_swarm/
├── __init__.py          # Package root
├── __main__.py          # Entry point — wires agents and launches the swarm
├── agent.py             # Base Agent class with message loop and error handling
├── cli.py               # UserAgent — interactive REPL bridging user and swarm
├── communication.py     # MessageBus, Message dataclass, SharedState
├── config.py            # YAML + environment variable configuration loader
├── controller.py        # Controller — pipeline orchestration and task routing
├── swarm.py             # Swarm manager — agent lifecycle and shutdown coordination
├── utils.py             # Shared utilities
└── workers.py           # PlannerAgent, CoderAgent, ReviewerAgent stubs
```

#### `Agent` (agent.py)

The base class for all agents. Provides:
- An async `run()` loop that processes messages from a per-agent inbox queue
- `send()` and `broadcast()` for directed and swarm-wide messaging
- Structured exception handling — `MessageHandlingError` for domain errors, common runtime exceptions caught to keep the loop alive

#### `MessageBus` (communication.py)

In-memory async message router. Each registered agent gets its own `asyncio.Queue`. Messages are either directed (routed to a specific agent's queue) or broadcast (copied to every queue). All messages are immutable `Message` dataclasses with unique IDs and timestamps.

#### `Controller` (controller.py)

The orchestration brain. Maintains a task registry and a per-request state machine (`RequestState`) that tracks each request through the `planning → coding → review → done` pipeline. Handles message routing between pipeline stages and notifies the user agent at each step.

#### `Swarm` (swarm.py)

Lifecycle manager. Spawns all agents concurrently via `asyncio.TaskGroup`, monitors for shutdown signals through a dedicated observer queue, and provides idempotent `stop()` for clean teardown.

#### `UserAgent` (cli.py)

Bridges the human user and the swarm. Runs a non-blocking REPL using `run_in_executor` for stdin reads. Sends `user_request` messages to the controller and waits for `user_output` responses, printing them as they arrive. Supports `quit`, `exit`, and `status` commands.

#### Workers (workers.py)

Three stub agents that demonstrate the collaboration pattern:
- **PlannerAgent** — decomposes a request into subtasks
- **CoderAgent** — generates placeholder code for each subtask
- **ReviewerAgent** — reviews code and returns a verdict

These are designed to be replaced with LLM-backed implementations. The orchestration layer does not change.

### Message Flow

All inter-agent communication uses typed messages:

| Message Type | Sender | Recipient | Purpose |
|---|---|---|---|
| `user_request` | UserAgent | Controller | New request from the user |
| `task_assign` | Controller | Worker | Assign a task to a worker agent |
| `task_result` | Worker | Controller | Return completed work |
| `user_output` | Controller | UserAgent | Status update or final result |
| `shutdown` | Any | Broadcast | Graceful swarm-wide shutdown |

## Development

### Running Tests

```bash
python -m pytest tests/ -v
```

### Linting

```bash
python -m ruff check src/ tests/
```

### Type Checking

```bash
python -m mypy src/
```

### All Checks

```bash
python -m ruff check src/ tests/ && python -m mypy src/ && python -m pytest tests/ -v
```

## Project Structure

```
agentic_swarm/
├── .github/workflows/ci.yml   # GitHub Actions — lint, typecheck, test (Python 3.11/3.12)
├── .editorconfig
├── .gitignore
├── pyproject.toml              # Project metadata, dependencies, tool configuration
├── requirements.txt
├── README.md
├── src/agentic_swarm/          # Source package
└── tests/                      # Test suite
```

## License

MIT

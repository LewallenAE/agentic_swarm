"""Configuration management - loads YAML and environment overrides."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise ImportError(
        "pyyaml is required: pip install pyyaml"
    ) from exc


def load_config(path: str | Path | None, env_prefix: str = "AGENTIC_SWARM_") -> dict[str, Any]:
    """Load configuration from YAML and merge environment overrides."""
    config: dict[str, Any] = {}

    if path is not None:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"config file not found: {path_obj}")
        data = yaml.safe_load(path_obj.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            config.update(data)

    env_overrides = _load_env_overrides(env_prefix)
    _deep_update(config, env_overrides)
    return config


def _load_env_overrides(prefix: str) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        path = key[len(prefix) :].lower().split("__")
        _set_nested(overrides, path, _parse_value(value))
    return overrides


def _parse_value(value: str) -> Any:
    try:
        return yaml.safe_load(value)
    except yaml.YAMLError:
        return value


def _set_nested(target: dict[str, Any], path: list[str], value: Any) -> None:
    current = target
    for segment in path[:-1]:
        if segment not in current or not isinstance(current[segment], dict):
            current[segment] = {}
        current = current[segment]
    current[path[-1]] = value


def _deep_update(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value

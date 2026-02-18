"""Tests for configuration loading."""
from __future__ import annotations

import pytest

from agentic_swarm.config import load_config


def test_load_config_env_override(tmp_path, monkeypatch) -> None:
    path = tmp_path / "config.yml"
    path.write_text("a:\n  b: 1\n", encoding="utf-8")

    monkeypatch.setenv("AGENTIC_SWARM_A__B", "2")

    config = load_config(path)
    assert config["a"]["b"] == 2


def test_load_config_missing_file(tmp_path) -> None:
    missing = tmp_path / "missing.yml"
    with pytest.raises(FileNotFoundError):
        load_config(missing)

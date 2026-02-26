"""Config file management for ~/.config/claude-project/."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "claude-project"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def save_config(config: dict[str, Any]) -> None:
    _ensure_dir()
    content = json.dumps(config, indent=2)
    # Write atomically with restricted permissions from the start
    fd = os.open(str(CONFIG_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, content.encode())
    finally:
        os.close(fd)


def get_session_key() -> str | None:
    return load_config().get("session_key")


def get_org_id() -> str | None:
    return load_config().get("org_id")


def set_session(session_key: str, org_id: str | None = None) -> None:
    config = load_config()
    config["session_key"] = session_key
    if org_id:
        config["org_id"] = org_id
    save_config(config)


def clear_session() -> None:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()

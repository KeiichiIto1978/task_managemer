#!/usr/bin/env python3
"""Shared helpers for MCP servers."""

from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.json"


@lru_cache(maxsize=1)
def load_environment(dotenv_path: Path | None = None) -> Dict[str, str]:
    """Load environment variables from .env once and return a copy."""
    env_path = dotenv_path or DEFAULT_ENV_PATH
    if env_path.exists():
        load_dotenv(env_path)
    # ensure PROJECT_ROOT is available for spawned processes
    os.environ.setdefault("PROJECT_ROOT", str(PROJECT_ROOT))

    project_root_str = str(PROJECT_ROOT)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    if os.environ.get("DEBUG_MCP_ENV") == "1":
        print(f"[servers.base] PROJECT_ROOT={PROJECT_ROOT}", file=sys.stderr)
        print(f"[servers.base] PYTHONPATH={os.environ.get('PYTHONPATH')}", file=sys.stderr)
        print(f"[servers.base] sys.path={sys.path}", file=sys.stderr)
    return dict(os.environ)


def get_env(key: str, *, required: bool = True) -> str:
    """Retrieve an environment variable, optionally enforcing presence."""
    load_environment()
    value = os.environ.get(key)
    if required and not value:
        raise RuntimeError(f"Environment variable '{key}' is required but not set.")
    return value or ""


@lru_cache(maxsize=1)
def load_settings() -> Dict[str, Any]:
    """Load application settings from config/settings.json."""
    if not SETTINGS_PATH.exists():
        raise FileNotFoundError(f"settings.json not found at {SETTINGS_PATH}")
    with open(SETTINGS_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def get_setting(*keys: str, default: Any = None) -> Any:
    """Fetch a nested setting value with a dotted path of keys."""
    data: Any = load_settings()
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key)
        if data is None:
            return default
    return data

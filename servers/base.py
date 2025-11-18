#!/usr/bin/env python3
"""Shared helpers for MCP servers."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.json"
LOGGER = logging.getLogger("mcp.base")
_LAST_GOOGLE_REFRESH: datetime | None = None


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


def _should_refresh(now: datetime, *, force: bool) -> bool:
    """Decide whether we should refresh based on last timestamp and threshold."""
    if force or _LAST_GOOGLE_REFRESH is None:
        return True
    threshold_hours = float(get_setting("security", "token_refresh_threshold_hours", default=1) or 1)
    if threshold_hours <= 0:
        return False
    threshold = timedelta(hours=threshold_hours)
    return now - _LAST_GOOGLE_REFRESH >= threshold


def maybe_refresh_google_tokens(*, force: bool = False) -> Dict[str, str]:
    """
    Refresh Google access tokens when auto-refresh is enabled or when forced.

    Returns a dict of updated token values (possibly empty).
    """

    from scripts.refresh_google_tokens import refresh_tokens  # Local import to avoid circular deps

    desktop_cfg = get_setting("desktop", default={}) or {}
    auto_refresh_enabled = bool(desktop_cfg.get("auto_refresh_google_tokens", False))

    if not auto_refresh_enabled and not force:
        return {}

    now = datetime.utcnow()
    if not _should_refresh(now, force=force):
        return {}

    persist_tokens = bool(desktop_cfg.get("persist_google_tokens", True))

    try:
        tokens = refresh_tokens(persist=persist_tokens, update_process_env=True)
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Failed to refresh Google tokens: %s", exc)
        raise

    global _LAST_GOOGLE_REFRESH  # noqa: PLW0603
    _LAST_GOOGLE_REFRESH = now
    LOGGER.info("Refreshed Google access tokens (persist=%s)", persist_tokens)
    return tokens

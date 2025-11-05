#!/usr/bin/env python3
"""Utility to refresh Google API access tokens and optionally update .env."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Iterable

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

SCOPES: Dict[str, str] = {
    "GMAIL": "https://www.googleapis.com/auth/gmail.readonly",
    "GOOGLE_CALENDAR": "https://www.googleapis.com/auth/calendar.readonly",
}

TOKEN_MAP = {
    "GMAIL": "GMAIL_ACCESS_TOKEN",
    "GOOGLE_CALENDAR": "GOOGLE_CALENDAR_ACCESS_TOKEN",
}

_cached_env: dict | None = None


def load_env_values(force: bool = False) -> dict:
    """Load environment variables from .env into a cached dictionary."""
    global _cached_env
    if force or _cached_env is None:
        if not ENV_FILE.exists():
            raise FileNotFoundError(f".env not found at {ENV_FILE}. Run setup.py first.")
        load_dotenv(ENV_FILE)
        _cached_env = dict(os.environ)
    return _cached_env


def get_required_env(key: str) -> str:
    value = load_env_values().get(key)
    if not value:
        raise RuntimeError(f"Environment variable '{key}' is required for token refresh.")
    return value


def refresh_token(prefix: str) -> str:
    """Refresh an access token for the given service prefix."""
    client_id = get_required_env(f"{prefix}_CLIENT_ID")
    client_secret = get_required_env(f"{prefix}_CLIENT_SECRET")
    refresh_token_value = get_required_env(f"{prefix}_REFRESH_TOKEN")
    scope = SCOPES[prefix]

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token_value,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[scope],
    )
    credentials.refresh(Request())
    return credentials.token


def update_env_file(env_path: Path, updates: dict[str, str]) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines()
    line_index = {line.split("=", 1)[0]: idx for idx, line in enumerate(lines) if "=" in line}

    for key, value in updates.items():
        if key in line_index:
            lines[line_index[key]] = f"{key}={value}"
        else:
            lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cache = load_env_values(force=True)
    cache.update(updates)


def set_process_env(updates: Iterable[tuple[str, str]]) -> None:
    for key, value in updates:
        os.environ[key] = value


def refresh_tokens(*, persist: bool = True, update_process_env: bool = True) -> dict[str, str]:
    """Refresh Google access tokens and optionally persist them to .env."""
    tokens: dict[str, str] = {}
    for prefix, env_key in TOKEN_MAP.items():
        tokens[env_key] = refresh_token(prefix)

    if persist:
        update_env_file(ENV_FILE, tokens)
    if update_process_env:
        set_process_env(tokens.items())
    return tokens


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh Google API access tokens and optionally update the .env file.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Refresh tokens without writing them back to .env (updates process env only).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational output (errors still reported).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        refresh_tokens(persist=not args.no_persist, update_process_env=True)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to refresh tokens: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.quiet:
        return

    if args.no_persist:
        print("Refreshed Google access tokens without modifying .env (process env updated).")
    else:
        print("Updated GMAIL_ACCESS_TOKEN and GOOGLE_CALENDAR_ACCESS_TOKEN in .env")


if __name__ == "__main__":
    main()
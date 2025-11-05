#!/usr/bin/env python3
"""Launch Claude Desktop with MCP environment variables loaded from .env."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.json"
ENV_PATH = PROJECT_ROOT / ".env"
SLACK_CACHE_DIR = PROJECT_ROOT / "cache" / "slack"


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        raise FileNotFoundError(f"settings.json not found at {SETTINGS_PATH}")
    with open(SETTINGS_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def ensure_env_loaded() -> None:
    if not ENV_PATH.exists():
        raise FileNotFoundError(f".env not found at {ENV_PATH}. Run setup.py and populate credentials.")
    load_dotenv(ENV_PATH)


def ensure_runtime_environment() -> None:
    """Populate environment variables required by local MCP servers."""
    os.environ.setdefault("PROJECT_ROOT", str(PROJECT_ROOT))
    os.environ.setdefault("PYTHON_EXECUTABLE", sys.executable)

    existing_pythonpath = os.environ.get("PYTHONPATH")
    if existing_pythonpath:
        paths = existing_pythonpath.split(os.pathsep)
        if str(PROJECT_ROOT) not in paths:
            os.environ["PYTHONPATH"] = os.pathsep.join([str(PROJECT_ROOT), existing_pythonpath])
    else:
        os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

    python_dir = str(Path(sys.executable).parent)
    current_path = os.environ.get("PATH", "")
    if python_dir not in current_path.split(os.pathsep):
        os.environ["PATH"] = os.pathsep.join([python_dir, current_path]) if current_path else python_dir


def cache_slack_metadata() -> None:
    """Fetch Slack channel metadata and write it to the local cache directory."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    workspace_id = os.environ.get("SLACK_WORKSPACE_ID")

    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is required but not set in the environment.")
    if not workspace_id:
        raise RuntimeError("SLACK_WORKSPACE_ID is required but not set in the environment.")

    client = WebClient(token=token, timeout=10)
    channels: list[dict[str, object]] = []
    cursor: str | None = None

    types = "public_channel,private_channel"
    try:
        while True:
            response = client.conversations_list(
                types=types,
                limit=200,
                cursor=cursor,
                exclude_archived=True,
            )
            channels.extend(response.get("channels", []))
            cursor = response.get("response_metadata", {}).get("next_cursor") or None
            if not cursor:
                break
    except SlackApiError as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to fetch Slack channel list: {exc.response['error']}") from exc

    simplified = []
    for entry in channels:
        channel_id = entry.get("id")
        name = entry.get("name")
        if not channel_id or not name:
            continue
        simplified.append(
            {
                "id": channel_id,
                "name": name,
                "is_private": entry.get("is_private"),
                "created": entry.get("created"),
                "num_members": entry.get("num_members"),
            }
        )

    SLACK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = SLACK_CACHE_DIR / f"{workspace_id}_channels.json"
    fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "workspace_id": workspace_id,
        "fetched_at": fetched_at,
        "channel_count": len(simplified),
        "channels": simplified,
    }
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Slack channel metadata cached to {cache_path}")


def should_refresh_tokens(settings: dict, args: argparse.Namespace) -> bool:
    desktop_cfg = settings.get("desktop", {})
    auto_refresh = bool(desktop_cfg.get("auto_refresh_google_tokens", False))

    if args.refresh_only:
        return True
    if args.no_refresh:
        return auto_refresh
    return True


def get_persist_preference(settings: dict, args: argparse.Namespace) -> bool:
    desktop_cfg = settings.get("desktop", {})
    default_persist = desktop_cfg.get("persist_google_tokens", True)

    if args.use_ephemeral_tokens:
        return False
    if args.persist_tokens:
        return True
    return bool(default_persist)


def maybe_refresh_tokens(settings: dict, args: argparse.Namespace, persist_tokens: bool) -> dict[str, str]:
    if not should_refresh_tokens(settings, args):
        return {}

    try:
        from refresh_google_tokens import refresh_tokens
    except ImportError as exc:  # noqa: BLE001
        raise RuntimeError("refresh_google_tokens.py is missing or has import errors") from exc

    return refresh_tokens(persist=persist_tokens, update_process_env=True)


def resolve_claude_path(settings: dict, override: str | None) -> Path:
    if override:
        candidate = Path(override).expanduser()
    else:
        desktop_cfg = settings.get("desktop", {})
        path_str = desktop_cfg.get("claude_path")
        if not path_str:
            raise RuntimeError("desktop.claude_path is not configured in settings.json")
        candidate = Path(path_str).expanduser()
    return candidate


def launch_claude(claude_path: Path, wait: bool) -> None:
    system = platform.system().lower()
    env = os.environ.copy()

    if system == "darwin":
        if claude_path.suffix == ".app" or claude_path.is_dir():
            cmd = ["open", str(claude_path)]
        else:
            cmd = ["open", "-a", str(claude_path)]
    elif system == "windows":
        if not claude_path.exists():
            raise FileNotFoundError(f"Claude Desktop executable not found: {claude_path}")
        cmd = [str(claude_path)]
    else:  # linux or others
        if claude_path.is_dir():
            raise RuntimeError("claude_path should point to the Claude executable, not a directory")
        cmd = [str(claude_path)]

    process = subprocess.Popen(cmd, env=env)
    print(f"Launched Claude Desktop (PID={process.pid}) with MCP environment variables.")
    if wait:
        process.wait()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Claude Desktop with .env credentials loaded.")
    parser.add_argument("--claude-path", help="Override path to Claude Desktop executable")
    parser.add_argument("--no-refresh", action="store_true", help="Do not refresh Google tokens unless settings.json enables auto-refresh")
    parser.add_argument("--wait", action="store_true", help="Wait for Claude Desktop process to exit")
    parser.add_argument("--refresh-only", action="store_true", help="Refresh Google tokens without launching Claude Desktop")

    token_group = parser.add_mutually_exclusive_group()
    token_group.add_argument("--use-ephemeral-tokens", action="store_true", help="Refresh tokens but keep them only in the current process environment")
    token_group.add_argument("--persist-tokens", action="store_true", help="Refresh tokens and force writing them to .env")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()

    ensure_env_loaded()
    ensure_runtime_environment()
    persist_tokens = get_persist_preference(settings, args)
    refreshed = maybe_refresh_tokens(settings, args, persist_tokens)
    cache_slack_metadata()

    if args.refresh_only:
        target = "and persisted" if persist_tokens else "for current session"
        print(f"Google tokens refreshed {target}. Skipping Claude launch as requested.")
        return

    if refreshed and not persist_tokens:
        print("Google tokens refreshed for this session without modifying .env")

    claude_path = resolve_claude_path(settings, args.claude_path)
    launch_claude(claude_path, wait=args.wait)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Lightweight Slack MCP server integration test.

This script launches the Slack MCP server as a subprocess, performs the
JSON-RPC handshake, and exercises one or both MCP tools without going
through Claude Desktop. Use it to verify environment variables, token
scopes, and recent code changes locally (and cheaply).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


def _load_env() -> None:
    """Load environment variables from .env once."""
    if getattr(_load_env, "_loaded", False):
        return
    if DEFAULT_ENV_PATH.exists():
        from dotenv import load_dotenv

        load_dotenv(DEFAULT_ENV_PATH)
    _load_env._loaded = True


def _read_json_line(stream) -> Optional[Dict[str, Any]]:
    """Read lines until a valid JSON object is parsed, otherwise return None."""
    start = time.time()
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            # The server may emit banners/log lines that are not JSON.
            # Ignore them and continue.
            if time.time() - start > 5:
                return None


def _send(process: subprocess.Popen, payload: Dict[str, Any]) -> None:
    line = json.dumps(payload)
    process.stdin.write(line + "\n")
    process.stdin.flush()


def call_tool(
    process: subprocess.Popen,
    tool_name: str,
    arguments: Dict[str, Any],
    request_id: int,
    verbose: bool,
) -> Dict[str, Any]:
    """Invoke an MCP tool and return the result payload."""
    _send(
        process,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
    )

    while True:
        response = _read_json_line(process.stdout)
        if response is None:
            raise RuntimeError(f"No JSON response received for tool '{tool_name}'.")
        if verbose:
            print(f"<- {json.dumps(response, ensure_ascii=False)}")
        if response.get("id") == request_id:
            return response


def run_tests(args: argparse.Namespace) -> int:
    """Launch the Slack MCP server and run the requested tests."""
    _load_env()
    env = os.environ.copy()
    if not env.get("SLACK_USER_TOKEN"):
        print("Error: SLACK_USER_TOKEN is required in the environment.", file=sys.stderr)
        return 1

    cmd = [sys.executable, "-m", "servers.slack_server"]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        # Handshake sequence
        _send(
            process,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "local-tester", "version": "0.1.0"},
                },
            },
        )

        # Consume initialize response
        init_response = _read_json_line(process.stdout)
        if args.verbose:
            print(f"<- {json.dumps(init_response, ensure_ascii=False)}")
        if not init_response or "result" not in init_response:
            raise RuntimeError("Failed to initialize Slack MCP server.")

        # Notify server we are ready (optional but mirrors Claude behaviour)
        _send(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # List available tools for reference
        _send(process, {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        tools_response = _read_json_line(process.stdout)
        if args.verbose:
            print(f"<- {json.dumps(tools_response, ensure_ascii=False)}")

        # Test list_available_slack_channels
        print("Calling list_available_slack_channels...")
        channel_args = {
            "types": args.channel_types,
            "limit": args.limit,
        }
        channel_response = call_tool(
            process,
            "list_available_slack_channels",
            channel_args,
            request_id=2,
            verbose=args.verbose,
        )

        result_payload = channel_response.get("result", {})
        if result_payload.get("isError"):
            raise RuntimeError(channel_response["result"]["content"][0]["text"])

        content = result_payload.get("structuredContent")
        channels: list[Dict[str, Any]] = []
        if not content:
            print("Received response:", channel_response)
        else:
            channels = content.get("channels", [])
            print(f"Fetched {len(channels)} channels (limit {args.limit}).")
            if channels:
                print("First channel:", json.dumps(channels[0], ensure_ascii=False))

        # Determine which channel (if any) to use for message retrieval
        message_channel = args.channel
        if not message_channel and not args.skip_messages and channels:
            message_channel = channels[0]["id"]
            print(f"Auto-selecting first channel '{message_channel}' for message retrieval.")

        if message_channel:
            print(f"Calling list_recent_slack_messages for channel '{message_channel}'...")
            message_response = call_tool(
                process,
                "list_recent_slack_messages",
                {"channel": message_channel, "limit": args.message_limit},
                request_id=3,
                verbose=args.verbose,
            )

            if message_response.get("result", {}).get("isError"):
                raise RuntimeError(message_response["result"]["content"][0]["text"])

            msg_content = message_response.get("result", {}).get("structuredContent")
            if not msg_content:
                print("Received response:", message_response)
            else:
                messages = msg_content.get("messages", [])
                print(f"Fetched {len(messages)} messages.")
                if messages:
                    first_message = messages[0]
                    print("First message:", json.dumps(first_message, ensure_ascii=False))
        else:
            print("Skipping list_recent_slack_messages (no channel selected).")

        return 0

    finally:
        try:
            _send(process, {"jsonrpc": "2.0", "method": "shutdown"})
            process.terminate()
        except Exception:
            process.kill()
        process.wait(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Slack MCP server integration tests without Claude.",
    )
    parser.add_argument(
        "--channel",
        help="Optional channel ID to test list_recent_slack_messages.",
    )
    parser.add_argument(
        "--channel-types",
        default="public_channel,private_channel,im,mpim",
        help="Types passed to list_available_slack_channels (default: %(default)s).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of channels to fetch (default: %(default)s).",
    )
    parser.add_argument(
        "--message-limit",
        type=int,
        default=10,
        help="Number of messages to fetch when --channel is provided.",
    )
    parser.add_argument(
        "--skip-messages",
        action="store_true",
        help="Do not call list_recent_slack_messages even if channels are available.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print raw JSON messages exchanged with the MCP server.",
    )
    args = parser.parse_args()
    sys.exit(run_tests(args))


if __name__ == "__main__":
    main()

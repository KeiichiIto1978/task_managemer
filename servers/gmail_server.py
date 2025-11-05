#!/usr/bin/env python3
"""Gmail MCP server implementation."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

import requests
from fastmcp import FastMCP

from .base import get_env, load_environment

LOGGER = logging.getLogger("gmail_mcp")
API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


def _build_headers() -> Dict[str, str]:
    token = get_env("GMAIL_ACCESS_TOKEN")
    return {"Authorization": f"Bearer {token}"}


def _fetch_message_detail(message_id: str) -> Dict[str, Any]:
    response = requests.get(
        f"{API_BASE}/{message_id}",
        params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
        headers=_build_headers(),
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()

    headers = {h["name"]: h["value"] for h in payload.get("payload", {}).get("headers", [])}
    timestamp = headers.get("Date")

    return {
        "id": payload.get("id"),
        "threadId": payload.get("threadId"),
        "snippet": payload.get("snippet"),
        "subject": headers.get("Subject", ""),
        "from": headers.get("From", ""),
        "date": timestamp,
        "url": f"https://mail.google.com/mail/u/0/#inbox/{payload.get('id')}",
    }


def _list_recent_messages(max_results: int) -> List[Dict[str, Any]]:
    response = requests.get(
        API_BASE,
        params={"maxResults": max_results, "labelIds": "INBOX"},
        headers=_build_headers(),
        timeout=15,
    )
    response.raise_for_status()
    message_ids = [item["id"] for item in response.json().get("messages", [])]

    results: List[Dict[str, Any]] = []
    for message_id in message_ids:
        try:
            results.append(_fetch_message_detail(message_id))
        except requests.HTTPError as exc:
            LOGGER.warning("Failed to fetch message %s: %s", message_id, exc)
    return results


def build_server() -> FastMCP:
    """Construct the FastMCP server."""
    load_environment()
    mcp = FastMCP("gmail-mcp")

    @mcp.tool()
    def list_recent_gmail_messages(max_results: int = 5) -> Dict[str, Any]:
        """Return recent Gmail messages from the inbox."""
        if max_results < 1 or max_results > 50:
            raise ValueError("max_results must be between 1 and 50.")

        messages = _list_recent_messages(max_results)
        return {
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "count": len(messages),
            "messages": messages,
        }

    return mcp


def main() -> None:
    """Entry point for standalone execution."""
    logging.basicConfig(level=logging.INFO)
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()

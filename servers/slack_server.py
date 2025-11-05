#!/usr/bin/env python3
"""Slack MCP server implementation."""

from __future__ import annotations

import logging
import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict

from fastmcp import FastMCP
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .base import PROJECT_ROOT, get_env, load_environment

LOGGER = logging.getLogger("slack_mcp")
SLACK_CACHE_DIR = PROJECT_ROOT / "cache" / "slack"
CONVERSATION_TYPES = {"public_channel", "private_channel", "mpim", "im"}
RESOLVE_FALLBACK_TYPES = ("public_channel", "private_channel")


@lru_cache(maxsize=1)
def _client() -> WebClient:
    token = get_env("SLACK_BOT_TOKEN")
    return WebClient(token=token, timeout=10)


@lru_cache(maxsize=1)
def _user_client() -> WebClient | None:
    load_environment()
    token = os.environ.get("SLACK_USER_TOKEN")
    if not token:
        LOGGER.debug("SLACK_USER_TOKEN not configured; DM and private channel history may be limited.")
        return None
    return WebClient(token=token, timeout=10)


def _format_ts(ts: str | None) -> str | None:
    if not ts:
        return None
    try:
        seconds = float(ts)
    except (TypeError, ValueError):
        return ts
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


def _workspace_id() -> str:
    return get_env("SLACK_WORKSPACE_ID")


def _load_cached_channels() -> Dict[str, str]:
    cache_file = SLACK_CACHE_DIR / f"{_workspace_id()}_channels.json"
    if not cache_file.exists():
        LOGGER.warning("Slack channel cache not found at %s", cache_file)
        return {}

    try:
        with open(cache_file, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, ValueError) as exc:  # noqa: BLE001
        LOGGER.warning("Failed to read Slack channel cache: %s", exc)
        return {}

    channels = {}
    for entry in data.get("channels", []):
        name = entry.get("name")
        channel_id = entry.get("id")
        if not name or not channel_id:
            continue
        channels[name] = channel_id
        channels[f"#{name}"] = channel_id
        channels[name.lower()] = channel_id
        channels[f"#{name.lower()}"] = channel_id
    return channels


def _looks_like_channel_id(identifier: str) -> bool:
    if not identifier:
        return False
    prefix = identifier[0]
    return prefix in {"C", "G", "D"} and len(identifier) >= 9


def _resolve_channel_identifier(raw: str, client: WebClient) -> str:
    identifier = raw.strip()
    if _looks_like_channel_id(identifier):
        return identifier

    normalized = identifier.lstrip("#")
    cache = _load_cached_channels()
    for key in (identifier, normalized, normalized.lower(), f"#{normalized}", f"#{normalized.lower()}"):
        channel_id = cache.get(key)
        if channel_id:
            LOGGER.info("Resolved Slack channel '%s' to ID '%s' via cache", raw, channel_id)
            return channel_id

    # Fallback to user conversations if cache miss
    user_client = _user_client()
    if user_client:
        conversation_types = ",".join(CONVERSATION_TYPES)
        cursor: str | None = None
        while True:
            try:
                response = user_client.users_conversations(types=conversation_types, limit=200, cursor=cursor)
            except SlackApiError as exc:  # noqa: BLE001
                LOGGER.debug("Slack users_conversations lookup failed: %s", exc.response.get("error"))
                break

            for channel_info in response.get("channels", []):
                channel_id = channel_info.get("id")
                if not channel_id:
                    continue

                lookup_keys = {channel_id}
                name = channel_info.get("name")
                if name:
                    lookup_keys.update({name, f"#{name}", name.lower(), f"#{name.lower()}"})
                if channel_info.get("is_im"):
                    user_id = channel_info.get("user")
                    if user_id:
                        lookup_keys.update({user_id, user_id.lower()})

                if identifier in lookup_keys or normalized in lookup_keys or normalized.lower() in lookup_keys:
                    LOGGER.info("Resolved Slack channel '%s' to ID '%s' via users.conversations", raw, channel_id)
                    return channel_id

            cursor = response.get("response_metadata", {}).get("next_cursor") or None
            if not cursor:
                break

    # Final fallback to bot conversations lookup
    conversation_types = ",".join(RESOLVE_FALLBACK_TYPES)
    cursor = None
    while True:
        try:
            response = client.conversations_list(
                types=conversation_types, limit=200, cursor=cursor, exclude_archived=True
            )
        except SlackApiError as exc:  # noqa: BLE001
            LOGGER.debug("Slack conversations_list lookup failed: %s", exc.response.get("error"))
            break

        for channel_info in response.get("channels", []):
            channel_id = channel_info.get("id")
            if not channel_id:
                continue

            lookup_keys = {channel_id}
            name = channel_info.get("name")
            if name:
                lookup_keys.update({name, f"#{name}", name.lower(), f"#{name.lower()}"})
            if channel_info.get("is_im"):
                user_id = channel_info.get("user")
                if user_id:
                    lookup_keys.update({user_id, user_id.lower()})

            if identifier in lookup_keys or normalized in lookup_keys or normalized.lower() in lookup_keys:
                LOGGER.info("Resolved Slack channel '%s' to ID '%s' via conversations.list (bot)", raw, channel_id)
                return channel_id

        cursor = response.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break

    raise RuntimeError(f"Slack channel '{raw}' could not be resolved to an ID. Refresh cache via start_claude_desktop.bat.")


def build_server() -> FastMCP:
    load_environment()
    mcp = FastMCP("slack-mcp")

    @mcp.tool()
    def list_recent_slack_messages(channel: str, limit: int = 10) -> Dict[str, Any]:
        """
        List recent messages from a Slack channel or DM.

        Args:
            channel: Channel ID (e.g. C123…) or user ID (for IM channels).
            limit: Number of messages to fetch (1-100).
        """

        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100.")

        bot_client = _client()
        user_client = _user_client()
        client: WebClient = bot_client
        channel_id = _resolve_channel_identifier(channel, bot_client)

        if channel_id.startswith("D"):
            if not user_client:
                raise RuntimeError("Slack user token (SLACK_USER_TOKEN) is required to fetch direct message history.")
            client = user_client

        try:
            history = client.conversations_history(channel=channel_id, limit=limit)
        except SlackApiError as exc:
            error_code = exc.response.get("error")
            if error_code in {"not_in_channel", "channel_not_found"} and user_client and client is not user_client:
                try:
                    history = user_client.conversations_history(channel=channel_id, limit=limit)
                    client = user_client
                except SlackApiError as retry_exc:
                    raise RuntimeError(f"Slack API error after retry with user token: {retry_exc.response['error']}") from retry_exc
            else:
                raise RuntimeError(f"Slack API error: {error_code}") from exc

        messages = []
        for msg in history.get("messages", []):
            messages.append(
                {
                    "text": msg.get("text", ""),
                    "user": msg.get("user"),
                    "ts": _format_ts(msg.get("ts")),
                    "thread_ts": _format_ts(msg.get("thread_ts")),
                    "permalink": msg.get("permalink"),
                }
            )

        return {
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "channel": channel_id,
            "count": len(messages),
            "messages": messages,
        }

    @mcp.tool()
    def list_available_slack_channels(
        types: str = "public_channel,private_channel", limit: int = 100, cursor: str | None = None
    ) -> Dict[str, Any]:
        """
        Retrieve channels the configured Slack token can access.

        Args:
            types: Comma-separated types passed to conversations.list (e.g. public_channel,private_channel,im,mpim).
            limit: Number of channels to fetch (1-200).
            cursor: Pagination cursor from a previous response.
        """

        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200.")

        user_client = _user_client()
        if not user_client:
            raise RuntimeError("SLACK_USER_TOKEN is required to list channels the user has joined.")

        requested_types = [entry.strip() for entry in types.split(",") if entry.strip()]
        if not requested_types:
            requested_types = ["public_channel", "private_channel"]

        unknown_types = [t for t in requested_types if t not in CONVERSATION_TYPES]
        if unknown_types:
            raise ValueError(f"Unsupported Slack channel types: {', '.join(sorted(set(unknown_types)))}")

        if cursor and len(requested_types) != 1:
            raise RuntimeError("cursor parameter is only supported when requesting a single conversation type.")

        channels: list[dict[str, Any]] = []
        next_cursor: str | None = None

        for channel_type in requested_types:
            remaining = limit - len(channels)
            if remaining <= 0:
                break

            local_cursor: str | None = cursor if cursor and len(requested_types) == 1 else None

            while remaining > 0:
                page_limit = min(remaining, 200)
                try:
                    response = user_client.users_conversations(
                        types=channel_type,
                        limit=page_limit,
                        cursor=local_cursor,
                    )
                except SlackApiError as exc:
                    error_code = exc.response.get("error")
                    if error_code == "missing_scope":
                        LOGGER.warning(
                            "Skipping Slack conversation type '%s' due to missing scope: %s",
                            channel_type,
                            exc.response.get("needed"),
                        )
                        break
                    raise RuntimeError(f"Slack API error during users_conversations: {error_code}") from exc

                local_cursor = response.get("response_metadata", {}).get("next_cursor") or None

                for channel_info in response.get("channels", []):
                    channel_id = channel_info.get("id")
                    if not channel_id:
                        continue

                    if not channel_info.get("is_member", True):
                        continue

                    name = channel_info.get("name")
                    if channel_info.get("is_im") and not name:
                        name = channel_info.get("user")
                    if not name:
                        name = channel_id

                    is_channel = bool(channel_info.get("is_channel"))
                    is_im = bool(channel_info.get("is_im"))
                    is_mpim = bool(channel_info.get("is_mpim"))
                    is_private = bool(channel_info.get("is_private")) or is_im or is_mpim

                    channels.append(
                        {
                            "id": channel_id,
                            "name": name,
                            "is_private": is_private,
                            "is_channel": is_channel,
                            "is_im": is_im,
                            "is_mpim": is_mpim,
                        }
                    )

                    if len(channels) >= limit:
                        break

                if len(channels) >= limit or not local_cursor:
                    break

                remaining = limit - len(channels)

            if cursor and len(requested_types) == 1:
                next_cursor = local_cursor

        return {
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "count": len(channels),
            "types": ",".join(requested_types),
            "channels": channels,
            "next_cursor": next_cursor,
        }

    return mcp


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_server().run()


if __name__ == "__main__":
    main()

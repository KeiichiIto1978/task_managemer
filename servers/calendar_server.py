#!/usr/bin/env python3
"""Google Calendar MCP server implementation."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests
from fastmcp import FastMCP

from .base import get_env, get_setting, load_environment, maybe_refresh_google_tokens

LOGGER = logging.getLogger("calendar_mcp")
CALENDAR_API = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
REQUEST_TIMEOUT = 15


def _build_headers() -> Dict[str, str]:
    maybe_refresh_google_tokens()
    token = get_env("GOOGLE_CALENDAR_ACCESS_TOKEN")
    return {"Authorization": f"Bearer {token}"}


def _get_with_auto_refresh(url: str, *, params: Dict[str, Any]) -> requests.Response:
    headers = _build_headers()
    response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
    if response.status_code == 401:
        LOGGER.info("Calendar token appears expired. Refreshing and retrying once.")
        maybe_refresh_google_tokens(force=True)
        headers = _build_headers()
        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
    return response


def _list_events(calendar_id: str, time_min: datetime, time_max: datetime, limit: int) -> List[Dict[str, Any]]:
    response = _get_with_auto_refresh(
        CALENDAR_API.format(calendar_id=calendar_id),
        params={
            "timeMin": time_min.isoformat() + "Z",
            "timeMax": time_max.isoformat() + "Z",
            "singleEvents": True,
            "maxResults": limit,
            "orderBy": "startTime",
        },
    )
    response.raise_for_status()
    payload = response.json()

    events: List[Dict[str, Any]] = []
    for event in payload.get("items", []):
        start = event.get("start", {})
        end = event.get("end", {})
        events.append(
            {
                "id": event.get("id"),
                "summary": event.get("summary"),
                "description": event.get("description"),
                "location": event.get("location"),
                "start": start.get("dateTime") or start.get("date"),
                "end": end.get("dateTime") or end.get("date"),
                "htmlLink": event.get("htmlLink"),
            }
        )
    return events


def build_server() -> FastMCP:
    load_environment()
    mcp = FastMCP("calendar-mcp")

    @mcp.tool()
    def list_upcoming_events(calendar_id: str | None = None, days: int = 7, limit: int = 20) -> Dict[str, Any]:
        """
        List upcoming calendar events.

        Args:
            calendar_id: Calendar identifier. Defaults to the first entry in settings.json or 'primary'.
            days: How many days ahead to include.
            limit: Maximum number of events to return (1-100).
        """

        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100.")
        if days < 1 or days > 30:
            raise ValueError("days must be between 1 and 30.")

        default_calendars = get_setting("data_collection", "google_calendar", "calendar_ids", default=["primary"])
        resolved_calendar = calendar_id or (default_calendars[0] if default_calendars else "primary")

        now = datetime.utcnow()
        horizon = now + timedelta(days=days)

        events = _list_events(resolved_calendar, now, horizon, limit)
        return {
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "calendar_id": resolved_calendar,
            "days": days,
            "count": len(events),
            "events": events,
        }

    return mcp


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_server().run()


if __name__ == "__main__":
    main()

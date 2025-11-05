#!/usr/bin/env python3
"""Integration tests that exercise MCP server tools."""

from __future__ import annotations

import asyncio
import json
import os
import unittest

from dotenv import load_dotenv

from servers.gmail_server import build_server as build_gmail_server
from servers.slack_server import build_server as build_slack_server
from servers.github_server import build_server as build_github_server
from servers.calendar_server import build_server as build_calendar_server
from servers.notion_server import build_server as build_notion_server


def _call_tool(server, name: str, **arguments):
    """Helper to synchronously invoke an MCP tool."""
    tool_result = asyncio.run(server._tool_manager.call_tool(name, arguments))
    if getattr(tool_result, "structured_content", None):
        return tool_result.structured_content
    if getattr(tool_result, "content", None):
        item = tool_result.content[0]
        if hasattr(item, "text") and item.text:
            try:
                return json.loads(item.text)
            except json.JSONDecodeError:
                return item.text
        return item
    return tool_result


class ServerToolIntegrationTests(unittest.TestCase):
    """Verify each MCP server can execute its primary tool end-to-end."""

    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()

    def test_gmail_list_recent_messages(self) -> None:
        if not os.environ.get("GMAIL_ACCESS_TOKEN"):
            self.skipTest("GMAIL_ACCESS_TOKEN is not configured; skipping Gmail integration test")
        server = build_gmail_server()
        result = _call_tool(server, "list_recent_gmail_messages", max_results=3)
        self.assertIsInstance(result, dict)
        self.assertIn("messages", result)
        self.assertLessEqual(result.get("count", 0), 3)

    def test_slack_list_recent_messages(self) -> None:
        channel_id = os.environ.get("SLACK_TEST_CHANNEL_ID")
        if not channel_id or not os.environ.get("SLACK_BOT_TOKEN"):
            self.skipTest("Slack credentials are not configured; skipping Slack integration test")
        server = build_slack_server()
        result = _call_tool(server, "list_recent_slack_messages", channel=channel_id, limit=5)
        self.assertTrue(isinstance(result, dict) or isinstance(result, list))

    def test_github_list_assigned_issues(self) -> None:
        if not os.environ.get("GITHUB_TOKEN"):
            self.skipTest("GITHUB_TOKEN is not configured; skipping GitHub integration test")
        server = build_github_server()
        result = _call_tool(server, "list_assigned_github_issues", limit=5)
        self.assertIsInstance(result, dict)
        self.assertIn("issues", result)

    def test_calendar_list_upcoming_events(self) -> None:
        if not os.environ.get("GOOGLE_CALENDAR_ACCESS_TOKEN"):
            self.skipTest("GOOGLE_CALENDAR_ACCESS_TOKEN is not configured; skipping Calendar integration test")
        server = build_calendar_server()
        result = _call_tool(server, "list_upcoming_events", days=2, limit=5)
        self.assertIsInstance(result, dict)
        self.assertIn("events", result)

    def test_notion_list_tasks(self) -> None:
        if not os.environ.get("NOTION_TOKEN") or not os.environ.get("NOTION_DATABASE_ID"):
            self.skipTest("Notion credentials are not configured; skipping Notion integration test")
        server = build_notion_server()
        result = _call_tool(server, "list_notion_tasks", page_size=5)
        self.assertIsInstance(result, dict)
        self.assertIn("tasks", result)


if __name__ == "__main__":
    unittest.main()

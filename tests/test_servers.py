#!/usr/bin/env python3
"""Basic sanity tests for MCP server factories."""

from __future__ import annotations

import importlib
import unittest

try:  # runtime dependency is optional during development
    from fastmcp import FastMCP  # type: ignore
except ImportError:  # pragma: no cover - dependency not installed yet
    FastMCP = None  # type: ignore


SERVER_MODULES = [
    "servers.gmail_server",
    "servers.slack_server",
    "servers.github_server",
    "servers.calendar_server",
    "servers.notion_server",
]


class ServerBuildTests(unittest.TestCase):
    """Ensure each server module exposes a build_server factory."""

    def test_build_server_returns_object_with_run(self) -> None:
        if FastMCP is None:
            self.skipTest("fastmcp is not installed")
        for module_name in SERVER_MODULES:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertTrue(hasattr(module, "build_server"), "build_server missing")
                server = module.build_server()
                if FastMCP is not None:
                    self.assertIsInstance(server, FastMCP)
                self.assertTrue(hasattr(server, "run"), "server lacks run()")


if __name__ == "__main__":
    unittest.main()

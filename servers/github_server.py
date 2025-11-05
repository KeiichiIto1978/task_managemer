#!/usr/bin/env python3
"""GitHub MCP server implementation."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from fastmcp import FastMCP
from github import Github
from github.Issue import Issue

from .base import get_env, load_environment

LOGGER = logging.getLogger("github_mcp")


def _client() -> Github:
    token = get_env("GITHUB_TOKEN")
    return Github(token, per_page=50)


def _issue_to_dict(issue: Issue) -> Dict[str, Any]:
    return {
        "id": issue.id,
        "number": issue.number,
        "repository": issue.repository.full_name if issue.repository else None,
        "title": issue.title,
        "state": issue.state,
        "labels": [label.name for label in issue.labels],
        "html_url": issue.html_url,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
    }


def build_server() -> FastMCP:
    load_environment()
    mcp = FastMCP("github-mcp")

    @mcp.tool()
    def list_assigned_github_issues(limit: int = 20, state: str = "open") -> Dict[str, Any]:
        """
        Fetch issues assigned to the authenticated user.

        Args:
            limit: Maximum number of issues to return (1-50).
            state: Filter by state ('open', 'closed', or 'all').
        """

        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50.")
        if state not in {"open", "closed", "all"}:
            raise ValueError("state must be one of: open, closed, all.")

        gh = _client()
        user = gh.get_user()
        issues = user.get_issues(state=state)

        results: List[Dict[str, Any]] = []
        for issue in issues[:limit]:
            results.append(_issue_to_dict(issue))

        return {
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "count": len(results),
            "state": state,
            "issues": results,
        }

    return mcp


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_server().run()


if __name__ == "__main__":
    main()

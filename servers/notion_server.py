#!/usr/bin/env python3
"""Notion MCP server implementation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from notion_client import Client

from .base import get_env, load_environment

LOGGER = logging.getLogger("notion_mcp")


def _client() -> Client:
    token = get_env("NOTION_TOKEN")
    return Client(auth=token)


@lru_cache(maxsize=16)
def _database_properties(database_id: str) -> Dict[str, Any]:
    client = _client()
    response = client.databases.retrieve(database_id=database_id)
    return response.get("properties", {})


def _resolve_property_name(
    database_id: str,
    preferred: Optional[str],
    expected_type: str,
) -> Optional[str]:
    properties = _database_properties(database_id)

    if preferred and preferred in properties:
        return preferred

    if preferred:
        for name in properties:
            if name.lower() == preferred.lower():
                return name

    for name, info in properties.items():
        if info.get("type") == expected_type:
            return name
    return None


def _title_property(database_id: str) -> str:
    properties = _database_properties(database_id)
    for name, info in properties.items():
        if info.get("type") == "title":
            return name
    raise RuntimeError("No title property found in the Notion database.")


def _query_database(database_id: str, page_size: int) -> List[Dict[str, Any]]:
    client = _client()
    response = client.databases.query(database_id=database_id, page_size=page_size)

    results: List[Dict[str, Any]] = []
    for row in response.get("results", []):
        properties = row.get("properties", {})
        results.append(
            {
                "id": row.get("id"),
                "url": row.get("url"),
                "title": _extract_title(properties),
                "status": _extract_select(properties, "Status"),
                "priority": _extract_select(properties, "Priority"),
                "due_date": _extract_date(properties, "Due Date"),
            }
        )
    return results


def _extract_title(properties: Dict[str, Any]) -> str | None:
    for prop in properties.values():
        if prop.get("type") == "title":
            title = prop.get("title", [])
            if title:
                return title[0].get("plain_text")
    return None


def _extract_select(properties: Dict[str, Any], name: str) -> str | None:
    prop = properties.get(name)
    if not prop:
        return None
    if prop.get("type") == "select" and prop.get("select"):
        return prop["select"].get("name")
    return None


def _extract_date(properties: Dict[str, Any], name: str) -> str | None:
    prop = properties.get(name)
    if not prop:
        return None
    if prop.get("type") == "date" and prop.get("date"):
        return prop["date"].get("start")
    return None


def build_server() -> FastMCP:
    load_environment()
    mcp = FastMCP("notion-mcp")

    @mcp.tool()
    def list_notion_tasks(database_id: str | None = None, page_size: int = 20) -> Dict[str, Any]:
        """
        Fetch tasks from the configured Notion database.

        Args:
            database_id: Notion database ID. Defaults to NOTION_DATABASE_ID env value.
            page_size: Number of rows to fetch (1-100).
        """

        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100.")

        resolved_db = database_id or get_env("NOTION_DATABASE_ID")
        rows = _query_database(resolved_db, page_size)
        return {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "count": len(rows),
            "tasks": rows,
        }

    @mcp.tool()
    def create_notion_task(  # noqa: D401
        title: str,
        database_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        due_date: str | None = None,
        description: str | None = None,
        source_url: str | None = None,
        status_property: str = "Status",
        priority_property: str = "Priority",
        due_date_property: str = "Due Date",
        description_property: str = "Description",
        source_url_property: str = "Source URL",
    ) -> Dict[str, Any]:
        """
        Create a new task page in the configured Notion database.

        Args:
            title: タスク名（必須）。
            database_id: Notion データベース ID。省略時は NOTION_DATABASE_ID を利用。
            status: ステータス select の値。省略可。
            priority: 優先度 select の値。省略可。
            due_date: 期限（ISO 8601 もしくは YYYY-MM-DD）。空文字を渡すと未設定。
            description: 説明欄にセットするテキスト。空文字を渡すと未設定。
            source_url: 参照 URL。空文字を渡すと未設定。
            *_property: 各プロパティの名称。データベース側の実名に合わせて調整可能。
        """

        if not title.strip():
            raise ValueError("title is required to create a Notion task.")

        resolved_db = database_id or get_env("NOTION_DATABASE_ID")
        title_property_name = _title_property(resolved_db)
        props: Dict[str, Any] = {
            title_property_name: {
                "title": [{"text": {"content": title.strip()}}],
            },
        }

        if status is not None:
            resolved_status_property = _resolve_property_name(resolved_db, status_property, "select")
            if resolved_status_property:
                props[resolved_status_property] = {"select": {"name": status}}
            else:
                LOGGER.warning("Notion status property '%s' not found. Skipping.", status_property)

        if priority is not None:
            resolved_priority_property = _resolve_property_name(resolved_db, priority_property, "select")
            if resolved_priority_property:
                props[resolved_priority_property] = {"select": {"name": priority}}
            else:
                LOGGER.warning(
                    "Notion priority property '%s' not found. Skipping.", priority_property
                )

        if due_date is not None:
            resolved_due_date_property = _resolve_property_name(resolved_db, due_date_property, "date")
            if resolved_due_date_property:
                if due_date.strip():
                    props[resolved_due_date_property] = {"date": {"start": due_date.strip()}}
                else:
                    props[resolved_due_date_property] = {"date": None}
            else:
                LOGGER.warning(
                    "Notion due date property '%s' not found. Skipping.", due_date_property
                )

        if description is not None:
            resolved_desc_property = _resolve_property_name(resolved_db, description_property, "rich_text")
            if resolved_desc_property:
                if description.strip():
                    props[resolved_desc_property] = {
                        "rich_text": [{"text": {"content": description}}]
                    }
                else:
                    props[resolved_desc_property] = {"rich_text": []}
            else:
                LOGGER.warning(
                    "Notion description property '%s' not found. Skipping.", description_property
                )

        if source_url is not None:
            resolved_url_property = _resolve_property_name(resolved_db, source_url_property, "url")
            if resolved_url_property:
                props[resolved_url_property] = {"url": source_url or None}
            else:
                LOGGER.warning(
                    "Notion source_url property '%s' not found. Skipping.", source_url_property
                )

        client = _client()
        page = client.pages.create(parent={"database_id": resolved_db}, properties=props)
        return {"id": page.get("id"), "url": page.get("url")}

    @mcp.tool()
    def update_notion_task(  # noqa: D401
        page_id: str,
        title: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        due_date: Optional[str] = None,
        description: Optional[str] = None,
        source_url: Optional[str] = None,
        database_id: str | None = None,
        status_property: str = "Status",
        priority_property: str = "Priority",
        due_date_property: str = "Due Date",
        description_property: str = "Description",
        source_url_property: str = "Source URL",
    ) -> Dict[str, Any]:
        """
        Update an existing Notion task page.

        Args:
            page_id: 更新対象のページ ID。
            title: 新しいタイトル。省略時は変更なし。空文字を渡すと未設定。
            status: ステータス select の値。省略時は変更なし。
            priority: 優先度 select の値。省略時は変更なし。
            due_date: 新しい期限。空文字を渡すと未設定。
            description: 説明文。空文字でクリア。
            source_url: 参照 URL。空文字でクリア。
            database_id: プロパティ解決用のデータベース ID（省略時は NOTION_DATABASE_ID）。
            *_property: 各プロパティ名称。データベースの名称と合わせる。
        """

        if not page_id.strip():
            raise ValueError("page_id is required to update a Notion task.")

        resolved_db = database_id or get_env("NOTION_DATABASE_ID")
        payload: Dict[str, Any] = {}

        if title is not None:
            title_property_name = _title_property(resolved_db)
            if title.strip():
                payload[title_property_name] = {"title": [{"text": {"content": title.strip()}}]}
            else:
                payload[title_property_name] = {"title": []}

        if status is not None:
            resolved_status_property = _resolve_property_name(resolved_db, status_property, "select")
            if resolved_status_property:
                payload[resolved_status_property] = {"select": {"name": status}}
            else:
                LOGGER.warning("Notion status property '%s' not found. Skipping.", status_property)

        if priority is not None:
            resolved_priority_property = _resolve_property_name(resolved_db, priority_property, "select")
            if resolved_priority_property:
                payload[resolved_priority_property] = {"select": {"name": priority}}
            else:
                LOGGER.warning(
                    "Notion priority property '%s' not found. Skipping.", priority_property
                )

        if due_date is not None:
            resolved_due_property = _resolve_property_name(resolved_db, due_date_property, "date")
            if resolved_due_property:
                if due_date.strip():
                    payload[resolved_due_property] = {"date": {"start": due_date.strip()}}
                else:
                    payload[resolved_due_property] = {"date": None}
            else:
                LOGGER.warning(
                    "Notion due date property '%s' not found. Skipping.", due_date_property
                )

        if description is not None:
            resolved_desc_property = _resolve_property_name(resolved_db, description_property, "rich_text")
            if resolved_desc_property:
                if description.strip():
                    payload[resolved_desc_property] = {
                        "rich_text": [{"text": {"content": description}}]
                    }
                else:
                    payload[resolved_desc_property] = {"rich_text": []}
            else:
                LOGGER.warning(
                    "Notion description property '%s' not found. Skipping.", description_property
                )

        if source_url is not None:
            resolved_url_property = _resolve_property_name(resolved_db, source_url_property, "url")
            if resolved_url_property:
                payload[resolved_url_property] = {"url": source_url or None}
            else:
                LOGGER.warning(
                    "Notion source_url property '%s' not found. Skipping.", source_url_property
                )

        if not payload:
            raise ValueError("No properties were provided to update.")

        client = _client()
        page = client.pages.update(page_id=page_id, properties=payload)
        return {"id": page.get("id"), "url": page.get("url")}

    return mcp


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_server().run()


if __name__ == "__main__":
    main()

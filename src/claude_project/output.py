"""Dual-mode output: rich tables to stderr, JSON to stdout."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Rich output goes to stderr so stdout stays clean for JSON piping
console = Console(stderr=True)


def _to_serializable(data: Any) -> Any:
    """Convert data to JSON-serializable form."""
    if isinstance(data, list):
        return [_to_serializable(d) for d in data]
    if hasattr(data, "to_dict"):
        return data.to_dict()
    return data


def render_json(data: Any) -> None:
    """Print JSON to stdout."""
    print(json.dumps(_to_serializable(data), indent=2, default=str))


def render_table(rows: list[dict], columns: list[str], title: str = "") -> None:
    """Render a rich table to stderr."""
    table = Table(title=title, show_lines=False)
    for col in columns:
        table.add_column(col, style="cyan" if col in ("uuid", "id") else None)
    for row in rows:
        table.add_row(*[str(row.get(col, "")) for col in columns])
    console.print(table)


def render_detail(data: dict, title: str = "") -> None:
    """Render a single object as a panel."""
    lines = []
    for k, v in data.items():
        if isinstance(v, str) and len(v) > 200:
            v = v[:200] + "..."
        lines.append(f"[bold]{k}:[/bold] {v}")
    console.print(Panel("\n".join(lines), title=title))


def render(
    data: Any,
    *,
    json_mode: bool = False,
    columns: list[str] | None = None,
    title: str = "",
) -> None:
    """Unified render function."""
    if json_mode:
        render_json(data)
        return

    if isinstance(data, list):
        if not data:
            console.print("[dim]No results.[/dim]")
            return
        items = [d.to_dict() if hasattr(d, "to_dict") else d for d in data]
        cols = columns or list(items[0].keys())
        render_table(items, cols, title=title)
    elif hasattr(data, "to_dict"):
        render_detail(data.to_dict(), title=title)
    elif isinstance(data, dict):
        render_detail(data, title=title)
    else:
        console.print(str(data))

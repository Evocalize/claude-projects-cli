"""Docs CLI commands."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer

from claude_project.cli import handle_errors
from claude_project.client.api import ClaudeAPIClient
from claude_project.exceptions import CLIError
from claude_project.output import console, render

app = typer.Typer(help="Manage project knowledge docs.")


@app.command("list")
@handle_errors
def list_docs(
    project_id: str = typer.Argument(help="Project UUID"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """List docs in a project."""

    async def _run():
        async with ClaudeAPIClient() as client:
            return await client.list_docs(project_id)

    docs = asyncio.run(_run())
    render(
        docs,
        json_mode=json_mode,
        columns=["file_name", "uuid", "token_count", "created_at"],
        title="Knowledge Docs",
    )


@app.command("add")
@handle_errors
def add_doc(
    project_id: str = typer.Argument(help="Project UUID"),
    file: Path | None = typer.Option(None, help="File to upload"),
    name: str | None = typer.Option(None, help="Document name (required with --content or stdin)"),
    content: str | None = typer.Option(None, help="Document content text"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Add a knowledge doc to a project.

    Supports --file, --name + --content, or piping via stdin (requires --name).
    """
    if file:
        file_name = file.name
        try:
            file_content = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise CLIError(f"Cannot read {file}: file is not valid UTF-8 text.")
    elif name and content:
        file_name = name
        file_content = content
    elif name and not sys.stdin.isatty():
        file_name = name
        file_content = sys.stdin.read()
        if not file_content.strip():
            raise CLIError("Empty content from stdin.")
    else:
        console.print("[red]Provide --file, --name + --content, or --name + stdin.[/red]")
        raise typer.Exit(1)

    async def _run():
        async with ClaudeAPIClient() as client:
            return await client.create_doc(project_id, file_name, file_content)

    doc = asyncio.run(_run())
    render(doc, json_mode=json_mode, title="Added Doc")


@app.command("rm")
@handle_errors
def remove_doc(
    project_id: str = typer.Argument(help="Project UUID"),
    doc_id: str = typer.Argument(help="Document UUID"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Remove a knowledge doc from a project."""

    async def _run():
        async with ClaudeAPIClient() as client:
            await client.delete_doc(project_id, doc_id)

    asyncio.run(_run())
    result = {"status": "deleted", "doc_id": doc_id}
    render(result, json_mode=json_mode, title="Removed Doc")

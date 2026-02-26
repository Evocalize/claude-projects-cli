"""Projects CLI commands."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer

from claude_project.cli import handle_errors
from claude_project.client.api import ClaudeAPIClient
from claude_project.output import console, render

app = typer.Typer(help="Manage projects.")


@app.command("list")
@handle_errors
def list_projects(
    limit: int = typer.Option(50, help="Max projects to return"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """List all projects."""

    async def _run():
        async with ClaudeAPIClient() as client:
            return await client.list_projects(limit=limit)

    projects = asyncio.run(_run())
    render(
        projects,
        json_mode=json_mode,
        columns=["name", "uuid", "updated_at", "is_starred"],
        title="Projects",
    )


@app.command("get")
@handle_errors
def get_project(
    project_id: str = typer.Argument(help="Project UUID"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Get project details."""

    async def _run():
        async with ClaudeAPIClient() as client:
            return await client.get_project(project_id)

    project = asyncio.run(_run())
    render(project, json_mode=json_mode, title=f"Project: {project.name}")


@app.command("create")
@handle_errors
def create_project(
    name: str = typer.Option(..., help="Project name"),
    description: str = typer.Option("", help="Project description"),
    private: bool = typer.Option(False, "--private", help="Make project private"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Create a new project."""

    async def _run():
        async with ClaudeAPIClient() as client:
            return await client.create_project(name, description, private)

    project = asyncio.run(_run())
    render(project, json_mode=json_mode, title="Created Project")


@app.command("update")
@handle_errors
def update_project(
    project_id: str = typer.Argument(help="Project UUID"),
    name: str | None = typer.Option(None, help="New name"),
    description: str | None = typer.Option(None, help="New description"),
    instructions: str | None = typer.Option(None, help="New project instructions"),
    instructions_file: Path | None = typer.Option(None, help="Read instructions from file"),
    star: bool | None = typer.Option(None, "--star/--unstar", help="Star or unstar"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Update a project."""
    update_kwargs: dict = {}
    if name is not None:
        update_kwargs["name"] = name
    if description is not None:
        update_kwargs["description"] = description
    if instructions is not None:
        update_kwargs["prompt_template"] = instructions
    if instructions_file is not None:
        update_kwargs["prompt_template"] = instructions_file.read_text()
    if star is not None:
        update_kwargs["is_starred"] = star

    if not update_kwargs:
        console.print("[red]No update fields provided.[/red]")
        raise typer.Exit(1)

    async def _run():
        async with ClaudeAPIClient() as client:
            return await client.update_project(project_id, **update_kwargs)

    project = asyncio.run(_run())
    render(project, json_mode=json_mode, title="Updated Project")


@app.command("delete")
@handle_errors
def delete_project(
    project_id: str = typer.Argument(help="Project UUID"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Delete a project."""
    if not confirm:
        if not sys.stdin.isatty():
            console.print("[red]Non-interactive mode requires --confirm / -y.[/red]")
            raise typer.Exit(1)
        typer.confirm(f"Delete project {project_id}?", abort=True)

    async def _run():
        async with ClaudeAPIClient() as client:
            await client.delete_project(project_id)

    asyncio.run(_run())
    result = {"status": "deleted", "project_id": project_id}
    render(result, json_mode=json_mode, title="Deleted")

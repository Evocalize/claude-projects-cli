"""Auth CLI commands: login, status, logout."""

from __future__ import annotations

import asyncio

import typer

from claude_project.auth.config import clear_session, get_org_id, get_session_key, set_session
from claude_project.auth.cookies import extract_session_key_browser
from claude_project.cli import handle_errors
from claude_project.client.api import ClaudeAPIClient
from claude_project.output import console, render

app = typer.Typer(help="Manage authentication.")


@app.command()
@handle_errors
def login(
    cookie: str | None = typer.Option(None, help="Manually provide sessionKey cookie value"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Login via browser (default) or by providing a cookie manually."""

    async def _run():
        if cookie:
            session_key = cookie
        else:
            console.print("Opening browser to claude.ai for login...")
            console.print("[dim]Log in if needed — the cookie will be captured automatically.[/dim]")
            session_key = await extract_session_key_browser()

        set_session(session_key)
        async with ClaudeAPIClient(session_key) as client:
            data = await client.bootstrap()
            account = data.get("account", {})
            memberships = account.get("memberships", [])
            org_name = ""
            if memberships:
                org = memberships[0].get("organization", {})
                org_name = org.get("name", "")
            return {
                "status": "authenticated",
                "email": account.get("email_address", ""),
                "org": org_name,
                "org_id": client._org_id,
            }

    result = asyncio.run(_run())
    render(result, json_mode=json_mode, title="Login Successful")


@app.command()
@handle_errors
def status(
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Show current authentication status."""
    session_key = get_session_key()
    if not session_key:
        result = {"status": "not authenticated"}
        render(result, json_mode=json_mode, title="Auth Status")
        raise typer.Exit(2)

    org_id = get_org_id()
    result = {
        "status": "authenticated",
        "org_id": org_id or "unknown",
        "session_key": session_key[:8] + "..." + session_key[-4:] if len(session_key) > 12 else "***",
    }
    render(result, json_mode=json_mode, title="Auth Status")


@app.command()
@handle_errors
def logout(
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Clear stored credentials."""
    clear_session()
    result = {"status": "logged out"}
    render(result, json_mode=json_mode, title="Logout")

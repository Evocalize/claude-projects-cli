"""Chat CLI commands."""

from __future__ import annotations

import asyncio
import sys

import typer

from claude_project.cli import handle_errors
from claude_project.client.api import ClaudeAPIClient
from claude_project.output import console, render

app = typer.Typer(help="Chat within a project scope.")


async def _stream_response(
    client: ClaudeAPIClient,
    conversation_id: str,
    prompt: str,
    model: str,
    json_mode: bool,
) -> str:
    """Stream a response, printing chunks or accumulating for JSON."""
    from rich.live import Live
    from rich.markdown import Markdown

    full_response = ""

    if json_mode:
        async for chunk in client.send_message_stream(conversation_id, prompt, model):
            full_response += chunk
    else:
        with Live(console=console, refresh_per_second=8) as live:
            async for chunk in client.send_message_stream(conversation_id, prompt, model):
                full_response += chunk
                live.update(Markdown(full_response))

    return full_response


async def _one_shot(
    project_id: str, prompt: str, model: str, json_mode: bool
) -> dict:
    """Create ephemeral conversation, get response, delete conversation."""
    async with ClaudeAPIClient() as client:
        conv = await client.create_conversation(project_id, model)
        try:
            response = await _stream_response(
                client, conv.uuid, prompt, model, json_mode
            )
        finally:
            try:
                await client.delete_conversation(conv.uuid)
            except Exception:
                pass

        return {
            "response": response,
            "conversation_id": conv.uuid,
            "model": model,
        }


async def _interactive(project_id: str, model: str, json_mode: bool) -> None:
    """Interactive REPL chat session."""
    async with ClaudeAPIClient() as client:
        conv = await client.create_conversation(project_id, model)
        console.print(
            f"[bold]Chat started[/bold] (project: {project_id[:8]}..., conv: {conv.uuid[:8]}...)"
        )
        console.print("[dim]Type /exit to quit.[/dim]\n")

        try:
            while True:
                try:
                    user_input = console.input("[bold blue]You:[/bold blue] ")
                except (EOFError, KeyboardInterrupt):
                    break

                if user_input.strip().lower() in ("/exit", "/quit"):
                    break
                if not user_input.strip():
                    continue

                console.print()
                response = await _stream_response(
                    client, conv.uuid, user_input, model, json_mode
                )
                console.print()
        finally:
            try:
                await client.delete_conversation(conv.uuid)
            except Exception:
                pass

        console.print("[dim]Chat ended.[/dim]")


@app.command("send")
@handle_errors
def send(
    project_id: str = typer.Argument(help="Project UUID"),
    message: str | None = typer.Argument(None, help="Message to send"),
    interactive: bool = typer.Option(False, "-i", "--interactive", help="Interactive REPL mode"),
    model: str = typer.Option("claude-sonnet-4-6", help="Model to use"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON output"),
):
    """Send a message or start an interactive chat."""
    if interactive:
        asyncio.run(_interactive(project_id, model, json_mode))
        return

    # Get message from arg or stdin
    if message is None:
        if sys.stdin.isatty():
            console.print("[red]Provide a message argument or pipe via stdin.[/red]")
            raise typer.Exit(1)
        message = sys.stdin.read().strip()
        if not message:
            console.print("[red]Empty message.[/red]")
            raise typer.Exit(1)

    result = asyncio.run(_one_shot(project_id, message, model, json_mode))
    if json_mode:
        render(result, json_mode=True)
    else:
        # In non-JSON mode, the response was already streamed to stderr via Rich Live.
        # Also write it to stdout so it's capturable via piping.
        print(result["response"])

"""Main CLI app with error handling and global --json flag."""

from __future__ import annotations

import functools
import json
import sys
from importlib.metadata import version

import typer

from claude_project import exceptions
from claude_project.exceptions import CLIError

app = typer.Typer(
    name="claude-project",
    help="CLI for managing Claude.ai Projects.",
    no_args_is_help=True,
)


def _version_callback(value: bool):
    if value:
        print(f"claude-project {version('claude-project')}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
):
    pass


def handle_errors(func):
    """Decorator to catch CLIError and format output."""

    # Track whether we've already handled an error (typer add_typer can double-invoke)
    _error_handled = False

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal _error_handled
        json_mode = kwargs.get("json_mode", False)
        exceptions.json_mode = json_mode
        try:
            return func(*args, **kwargs)
        except CLIError as e:
            if not _error_handled:
                _error_handled = True
                if exceptions.json_mode:
                    print(json.dumps({"error": e.message, "code": e.exit_code}))
                else:
                    from claude_project.output import console

                    console.print(f"[red]Error:[/red] {e.message}")
            raise typer.Exit(e.exit_code)

    return wrapper


def _setup():
    from claude_project.cli.auth import app as auth_app
    from claude_project.cli.chat import app as chat_app
    from claude_project.cli.docs import app as docs_app
    from claude_project.cli.projects import app as projects_app

    app.add_typer(auth_app, name="auth")
    app.add_typer(projects_app, name="projects")
    app.add_typer(docs_app, name="docs")
    app.add_typer(chat_app, name="chat")


_setup()


def entry():
    """Entry point."""
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(130)

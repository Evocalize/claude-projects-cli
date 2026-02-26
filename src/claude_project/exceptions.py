"""Error hierarchy with distinct exit codes."""

from __future__ import annotations

# Module-level flag set by CLI when --json is active.
# Used by error handlers to format output appropriately.
json_mode: bool = False


class CLIError(Exception):
    """Base error for claude-project CLI."""

    exit_code: int = 1

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AuthError(CLIError):
    """Authentication failed or missing."""

    exit_code = 2


class NotFoundError(CLIError):
    """Resource not found."""

    exit_code = 3


class RateLimitError(CLIError):
    """Rate limited by API."""

    exit_code = 4


class APIError(CLIError):
    """General API error."""

    exit_code = 5

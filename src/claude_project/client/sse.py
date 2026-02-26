"""SSE stream parser for Claude.ai completion responses."""

from __future__ import annotations

import json
import sys
from typing import AsyncIterator

import httpx

from claude_project.exceptions import APIError


async def parse_sse_stream(response: httpx.Response) -> AsyncIterator[str]:
    """Parse SSE stream, yielding text chunks from completion events.

    Claude.ai SSE format:
        event: completion
        data: {"type":"completion","completion":" text","stop_reason":null,...}
    """
    current_event = ""

    async for line in response.aiter_lines():
        if line.startswith("event: "):
            current_event = line[7:]
            continue

        if not line.startswith("data: "):
            continue

        raw = line[6:]
        if not raw or raw == "[DONE]":
            continue

        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            print(f"Warning: malformed SSE data: {raw[:100]}", file=sys.stderr)
            continue

        if event.get("type") == "error" or current_event == "error":
            msg = event.get("error", {}).get("message", str(event))
            raise APIError(f"Stream error: {msg}")

        if event.get("type") == "completion":
            text = event.get("completion", "")
            if text:
                yield text

            if event.get("stop_reason"):
                return

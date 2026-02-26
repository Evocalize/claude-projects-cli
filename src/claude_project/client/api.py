"""Async HTTP client for Claude.ai internal API."""

from __future__ import annotations

import time
from typing import AsyncIterator

import httpx

from claude_project.auth.config import get_org_id, get_session_key, save_config, load_config
from claude_project.client.sse import parse_sse_stream
from claude_project.exceptions import APIError, AuthError, NotFoundError, RateLimitError
from claude_project.models import Conversation, Document, Project

BASE_URL = "https://claude.ai"

# Fields the API accepts for project updates
_PROJECT_UPDATE_FIELDS = {"name", "description", "prompt_template", "is_private", "is_starred"}


def _detect_timezone() -> str:
    """Detect system timezone using Python stdlib."""
    try:
        tz = time.tzname[0]
        # Try to get the IANA timezone name on macOS/Linux
        import os
        tz_path = os.readlink("/etc/localtime")
        if "/zoneinfo/" in tz_path:
            return tz_path.split("/zoneinfo/")[-1]
    except (OSError, AttributeError):
        pass
    # Fallback: construct offset-based timezone
    offset = time.timezone if time.daylight == 0 else time.altzone
    hours = -offset // 3600
    return f"Etc/GMT{'+' if hours >= 0 else ''}{hours}" if hours != 0 else "UTC"


class ClaudeAPIClient:
    """Async context manager for Claude.ai API calls."""

    def __init__(self, session_key: str | None = None, org_id: str | None = None):
        self._session_key = session_key or get_session_key()
        if not self._session_key:
            raise AuthError("Not logged in. Run: claude-project auth login")
        self._org_id = org_id or get_org_id()
        self._timezone = _detect_timezone()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> ClaudeAPIClient:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            cookies={"sessionKey": self._session_key},
            headers={
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/json",
                "origin": "https://claude.ai",
                "referer": "https://claude.ai/",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            },
            timeout=60.0,
            follow_redirects=True,
        )
        if not self._org_id:
            await self._detect_org()
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    async def _raise_for_status(self, resp: httpx.Response, *, streamed: bool = False) -> None:
        if resp.status_code < 400:
            return
        # For streamed responses, read the body before parsing error details
        if streamed:
            await resp.aread()
        if resp.status_code in (401, 403):
            raise AuthError("Session expired or invalid. Run: claude-project auth login")
        if resp.status_code == 404:
            raise NotFoundError(f"Resource not found: {resp.url}")
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after", "")
            msg = "Rate limited."
            if retry_after:
                msg += f" Retry after {retry_after}s."
            else:
                msg += " Please wait and try again."
            raise RateLimitError(msg)
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            detail = resp.text
        raise APIError(f"API error {resp.status_code}: {detail}")

    def _org_url(self, path: str) -> str:
        return f"/api/organizations/{self._org_id}/{path}"

    # --- Bootstrap ---

    async def bootstrap(self) -> dict:
        resp = await self._client.get("/api/bootstrap")
        await self._raise_for_status(resp)
        return resp.json()

    async def _detect_org(self) -> None:
        """Auto-detect the right org by trying the projects endpoint on each.

        Prefers team orgs (raven_type=team), falls back to any org that works.
        """
        data = await self.bootstrap()
        account = data.get("account", {})
        memberships = account.get("memberships", [])
        if not memberships:
            raise AuthError("No organization found in account.")

        # Sort: team orgs first, then others
        sorted_memberships = sorted(
            memberships,
            key=lambda m: (0 if m.get("organization", {}).get("raven_type") == "team" else 1),
        )

        for m in sorted_memberships:
            org = m.get("organization", {})
            org_id = org.get("uuid")
            if not org_id:
                continue
            resp = await self._client.get(
                f"/api/organizations/{org_id}/projects",
                params={"limit": 1},
            )
            if resp.status_code == 200:
                self._org_id = org_id
                config = load_config()
                config["org_id"] = self._org_id
                config["org_name"] = org.get("name", "")
                save_config(config)
                return

        # If none worked, fall back to first
        org = memberships[0].get("organization", {})
        self._org_id = org.get("uuid", "")
        config = load_config()
        config["org_id"] = self._org_id
        save_config(config)

    # --- Projects ---

    async def list_projects(self, limit: int = 50) -> list[Project]:
        resp = await self._client.get(
            self._org_url("projects"),
            params={"limit": limit, "order_by": "latest_chat"},
        )
        await self._raise_for_status(resp)
        return [Project.from_api(p) for p in resp.json()]

    async def get_project(self, project_id: str) -> Project:
        resp = await self._client.get(self._org_url(f"projects/{project_id}"))
        await self._raise_for_status(resp)
        return Project.from_api(resp.json())

    async def create_project(
        self, name: str, description: str = "", is_private: bool = False
    ) -> Project:
        resp = await self._client.post(
            self._org_url("projects"),
            json={"name": name, "description": description, "is_private": is_private},
        )
        await self._raise_for_status(resp)
        return Project.from_api(resp.json())

    async def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        prompt_template: str | None = None,
        is_private: bool | None = None,
        is_starred: bool | None = None,
    ) -> Project:
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if prompt_template is not None:
            payload["prompt_template"] = prompt_template
        if is_private is not None:
            payload["is_private"] = is_private
        if is_starred is not None:
            payload["is_starred"] = is_starred
        resp = await self._client.put(
            self._org_url(f"projects/{project_id}"),
            json=payload,
        )
        await self._raise_for_status(resp)
        return Project.from_api(resp.json())

    async def delete_project(self, project_id: str) -> None:
        resp = await self._client.delete(self._org_url(f"projects/{project_id}"))
        await self._raise_for_status(resp)

    # --- Documents ---

    async def list_docs(self, project_id: str) -> list[Document]:
        resp = await self._client.get(self._org_url(f"projects/{project_id}/docs"))
        await self._raise_for_status(resp)
        return [Document.from_api(d) for d in resp.json()]

    async def create_doc(
        self, project_id: str, file_name: str, content: str
    ) -> Document:
        resp = await self._client.post(
            self._org_url(f"projects/{project_id}/docs"),
            json={"file_name": file_name, "content": content},
        )
        await self._raise_for_status(resp)
        return Document.from_api(resp.json())

    async def delete_doc(self, project_id: str, doc_id: str) -> None:
        resp = await self._client.delete(
            self._org_url(f"projects/{project_id}/docs/{doc_id}")
        )
        await self._raise_for_status(resp)

    # --- Conversations ---

    async def create_conversation(
        self, project_uuid: str, model: str = "claude-sonnet-4-6"
    ) -> Conversation:
        resp = await self._client.post(
            self._org_url("chat_conversations"),
            json={"name": "", "project_uuid": project_uuid, "model": model},
        )
        await self._raise_for_status(resp)
        return Conversation.from_api(resp.json())

    async def send_message_stream(
        self, conversation_id: str, prompt: str, model: str = "claude-sonnet-4-6"
    ) -> AsyncIterator[str]:
        req = self._client.build_request(
            "POST",
            self._org_url(f"chat_conversations/{conversation_id}/completion"),
            json={
                "prompt": prompt,
                "timezone": self._timezone,
                "model": model,
                "attachments": [],
                "files": [],
            },
        )
        resp = await self._client.send(req, stream=True)
        try:
            await self._raise_for_status(resp, streamed=True)
            async for chunk in parse_sse_stream(resp):
                yield chunk
        finally:
            await resp.aclose()

    async def delete_conversation(self, conversation_id: str) -> None:
        resp = await self._client.delete(
            self._org_url(f"chat_conversations/{conversation_id}")
        )
        await self._raise_for_status(resp)

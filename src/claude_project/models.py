"""Dataclass models for Claude.ai API objects."""

from __future__ import annotations

from dataclasses import dataclass

from claude_project.exceptions import APIError


def _require(data: dict, key: str) -> str:
    """Get a required field from API data, raising a clear error if missing."""
    value = data.get(key)
    if value is None:
        raise APIError(f"API response missing required field: {key}")
    return value


@dataclass
class Organization:
    uuid: str
    name: str

    @classmethod
    def from_api(cls, data: dict) -> Organization:
        return cls(uuid=_require(data, "uuid"), name=data.get("name", ""))


@dataclass
class Project:
    uuid: str
    name: str
    description: str = ""
    is_private: bool = False
    is_starred: bool = False
    prompt_template: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_api(cls, data: dict) -> Project:
        return cls(
            uuid=_require(data, "uuid"),
            name=_require(data, "name"),
            description=data.get("description", "") or "",
            is_private=data.get("is_private", False),
            is_starred=data.get("is_starred", False),
            prompt_template=data.get("prompt_template", "") or "",
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "description": self.description,
            "is_private": self.is_private,
            "is_starred": self.is_starred,
            "prompt_template": self.prompt_template,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Document:
    uuid: str
    file_name: str
    content: str = ""
    created_at: str = ""
    token_count: int | None = None

    @classmethod
    def from_api(cls, data: dict) -> Document:
        return cls(
            uuid=_require(data, "uuid"),
            file_name=_require(data, "file_name"),
            content=data.get("content", "") or "",
            created_at=data.get("created_at", ""),
            token_count=data.get("token_count"),
        )

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "file_name": self.file_name,
            "content": self.content,
            "created_at": self.created_at,
            "token_count": self.token_count,
        }


@dataclass
class Conversation:
    uuid: str
    name: str = ""
    project_uuid: str = ""
    model: str = ""
    created_at: str = ""

    @classmethod
    def from_api(cls, data: dict) -> Conversation:
        return cls(
            uuid=_require(data, "uuid"),
            name=data.get("name", "") or "",
            project_uuid=data.get("project_uuid", "") or "",
            model=data.get("model", "") or "",
            created_at=data.get("created_at", ""),
        )

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "project_uuid": self.project_uuid,
            "model": self.model,
            "created_at": self.created_at,
        }

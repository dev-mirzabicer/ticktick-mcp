"""
Unified Project Models.

This module provides canonical Project, ProjectGroup, Column,
and ProjectData models that combine V1 and V2 API representations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self, TYPE_CHECKING

from pydantic import Field, field_validator

from ticktick_mcp.constants import ProjectKind, ViewMode
from ticktick_mcp.models.base import TickTickModel

if TYPE_CHECKING:
    from ticktick_mcp.models.task import Task


class SortOption(TickTickModel):
    """Sorting configuration."""

    group_by: str | None = Field(default=None, alias="groupBy")
    order_by: str | None = Field(default=None, alias="orderBy")


class Column(TickTickModel):
    """Kanban column model."""

    id: str
    project_id: str = Field(alias="projectId")
    name: str
    sort_order: int | None = Field(default=None, alias="sortOrder")


class ProjectGroup(TickTickModel):
    """
    Project group/folder model.

    This is a V2-only feature for organizing projects.
    """

    id: str
    etag: str | None = None
    name: str

    # Display
    view_mode: str | None = Field(default=None, alias="viewMode")
    sort_option: SortOption | None = Field(default=None, alias="sortOption")
    sort_order: int | None = Field(default=None, alias="sortOrder")
    sort_type: str | None = Field(default=None, alias="sortType")

    # Status
    deleted: int = Field(default=0)
    show_all: bool = Field(default=False, alias="showAll")

    # Team
    team_id: Any | None = Field(default=None, alias="teamId")
    user_id: int | None = Field(default=None, alias="userId")

    @classmethod
    def from_v2(cls, data: dict[str, Any]) -> Self:
        """Create from V2 API response."""
        return cls.model_validate(data)

    def to_v2_create_dict(self) -> dict[str, Any]:
        """Convert to V2 API create format."""
        return {
            "name": self.name,
            "listType": "group",
        }

    def to_v2_update_dict(self) -> dict[str, Any]:
        """Convert to V2 API update format."""
        return {
            "id": self.id,
            "name": self.name,
            "listType": "group",
        }


class Project(TickTickModel):
    """
    Unified Project model.

    Combines V1 and V2 project representations.

    V1 fields: id, name, color, sortOrder, closed, groupId, viewMode, permission, kind
    V2 additional: etag, inAll, sortOption, sortType, modifiedTime, isOwner,
                   userCount, muted, transferred, teamId, notificationOptions,
                   openToTeam, teamMemberPermission, background, etc.
    """

    # Core identifiers
    id: str
    etag: str | None = None

    # Basic info
    name: str
    color: str | None = None
    kind: str | None = Field(default=ProjectKind.TASK)

    # Organization
    group_id: str | None = Field(default=None, alias="groupId")
    in_all: bool | None = Field(default=None, alias="inAll")
    view_mode: str | None = Field(default=ViewMode.LIST, alias="viewMode")
    sort_option: SortOption | None = Field(default=None, alias="sortOption")
    sort_order: int | None = Field(default=None, alias="sortOrder")
    sort_type: str | None = Field(default=None, alias="sortType")

    # Metadata
    modified_time: datetime | None = Field(default=None, alias="modifiedTime")
    is_owner: bool | None = Field(default=None, alias="isOwner")
    user_count: int | None = Field(default=None, alias="userCount")

    # Status
    closed: bool | None = None
    muted: bool | None = None

    # Permissions
    permission: str | None = None

    # Team/Sharing (V2 only)
    team_id: Any | None = Field(default=None, alias="teamId")
    open_to_team: bool | None = Field(default=None, alias="openToTeam")

    @field_validator("modified_time", mode="before")
    @classmethod
    def parse_datetime_field(cls, v: Any) -> datetime | None:
        return cls.parse_datetime(v)

    @property
    def is_inbox(self) -> bool:
        """Check if this is the inbox project."""
        return self.id.startswith("inbox")

    @property
    def is_closed(self) -> bool:
        """Check if the project is closed/archived."""
        return self.closed is True

    @property
    def is_note_project(self) -> bool:
        """Check if this is a notes project."""
        return self.kind == ProjectKind.NOTE

    @property
    def is_task_project(self) -> bool:
        """Check if this is a tasks project."""
        return self.kind == ProjectKind.TASK

    @property
    def view_mode_enum(self) -> ViewMode:
        """Get view mode as enum."""
        if self.view_mode:
            try:
                return ViewMode(self.view_mode)
            except ValueError:
                pass
        return ViewMode.LIST

    # V1/V2 conversion methods
    @classmethod
    def from_v1(cls, data: dict[str, Any]) -> Self:
        """Create from V1 API response."""
        return cls.model_validate(data)

    @classmethod
    def from_v2(cls, data: dict[str, Any]) -> Self:
        """Create from V2 API response."""
        return cls.model_validate(data)

    def to_v1_dict(self) -> dict[str, Any]:
        """Convert to V1 API format for requests."""
        data: dict[str, Any] = {}

        if self.name is not None:
            data["name"] = self.name
        if self.color is not None:
            data["color"] = self.color
        if self.sort_order is not None:
            data["sortOrder"] = self.sort_order
        if self.view_mode is not None:
            data["viewMode"] = self.view_mode
        if self.kind is not None:
            data["kind"] = self.kind

        return data

    def to_v2_create_dict(self) -> dict[str, Any]:
        """Convert to V2 API create format."""
        data: dict[str, Any] = {"name": self.name}

        if self.color is not None:
            data["color"] = self.color
        if self.kind is not None:
            data["kind"] = self.kind
        if self.view_mode is not None:
            data["viewMode"] = self.view_mode
        if self.group_id is not None:
            data["groupId"] = self.group_id
        if self.sort_order is not None:
            data["sortOrder"] = self.sort_order

        return data

    def to_v2_update_dict(self) -> dict[str, Any]:
        """Convert to V2 API update format."""
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
        }

        if self.color is not None:
            data["color"] = self.color
        if self.group_id is not None:
            data["groupId"] = self.group_id

        return data


class ProjectData(TickTickModel):
    """
    Project with its tasks and columns.

    This is primarily from V1's get_project_with_data endpoint.
    """

    project: Project
    tasks: list[Any] = Field(default_factory=list)  # Will be Task objects
    columns: list[Column] = Field(default_factory=list)

    @field_validator("columns", mode="before")
    @classmethod
    def parse_columns(cls, v: Any) -> list[Column]:
        if v is None:
            return []
        if isinstance(v, list):
            return [
                Column.model_validate(col) if isinstance(col, dict) else col
                for col in v
            ]
        return []

    @classmethod
    def from_v1(cls, data: dict[str, Any]) -> Self:
        """Create from V1 API response."""
        from ticktick_mcp.models.task import Task

        project = Project.from_v1(data.get("project", {}))
        tasks = [Task.from_v1(t) for t in data.get("tasks", [])]
        columns = [Column.model_validate(c) for c in data.get("columns", [])]

        return cls(project=project, tasks=tasks, columns=columns)

"""
Unified Task Model.

This module provides the canonical Task model that combines
V1 and V2 API task representations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from pydantic import Field, field_validator, model_validator

from ticktick_sdk.constants import (
    TaskKind,
    TaskPriority,
    TaskStatus,
    SubtaskStatus,
)
from ticktick_sdk.models.base import TickTickModel


class TaskReminder(TickTickModel):
    """Task reminder configuration."""

    id: str | None = None
    trigger: str  # ICalTrigger format, e.g., "TRIGGER:-PT30M"

    @classmethod
    def from_v1_string(cls, trigger: str) -> TaskReminder:
        """Create from V1 reminder string."""
        return cls(trigger=trigger)

    def to_v1_string(self) -> str:
        """Convert to V1 reminder string."""
        return self.trigger


class ChecklistItem(TickTickModel):
    """Subtask/checklist item model."""

    id: str
    title: str | None = None
    status: int = Field(default=SubtaskStatus.NORMAL)
    completed_time: datetime | None = Field(default=None, alias="completedTime")
    start_date: datetime | None = Field(default=None, alias="startDate")
    time_zone: str | None = Field(default=None, alias="timeZone")
    is_all_day: bool | None = Field(default=None, alias="isAllDay")
    sort_order: int | None = Field(default=None, alias="sortOrder")

    @property
    def is_completed(self) -> bool:
        """Check if the item is completed."""
        return self.status == SubtaskStatus.COMPLETED

    @field_validator("completed_time", "start_date", mode="before")
    @classmethod
    def parse_datetime_field(cls, v: Any) -> datetime | None:
        return cls.parse_datetime(v)


class Task(TickTickModel):
    """
    Unified Task model.

    This model combines all fields from both V1 and V2 APIs,
    providing a canonical representation for tasks.

    V1-only fields: (none - V2 is superset)
    V2-only fields: tags, parent_id, child_ids, etag, progress, deleted,
                    is_floating, creator, assignee, focus_summaries,
                    pomodoro_summaries, attachments, column_id, comment_count
    """

    # Core identifiers
    id: str
    project_id: str = Field(alias="projectId")
    etag: str | None = None

    # Content
    title: str | None = None
    content: str | None = None
    desc: str | None = None
    kind: str = Field(default=TaskKind.TEXT)

    # Status
    status: int = Field(default=TaskStatus.ACTIVE)
    priority: int = Field(default=TaskPriority.NONE)
    progress: int | None = None  # 0-100 for checklists
    deleted: int = Field(default=0)  # 0 or 1

    # Dates
    start_date: datetime | None = Field(default=None, alias="startDate")
    due_date: datetime | None = Field(default=None, alias="dueDate")
    created_time: datetime | None = Field(default=None, alias="createdTime")
    modified_time: datetime | None = Field(default=None, alias="modifiedTime")
    completed_time: datetime | None = Field(default=None, alias="completedTime")
    time_zone: str | None = Field(default=None, alias="timeZone")
    is_all_day: bool | None = Field(default=None, alias="isAllDay")
    is_floating: bool = Field(default=False, alias="isFloating")

    # Recurrence
    repeat_flag: str | None = Field(default=None, alias="repeatFlag")
    repeat_from: int | None = Field(default=None, alias="repeatFrom")
    repeat_first_date: datetime | None = Field(default=None, alias="repeatFirstDate")
    repeat_task_id: str | None = Field(default=None, alias="repeatTaskId")
    ex_date: list[str] | None = Field(default=None, alias="exDate")

    # Reminders
    reminder: str | None = None
    reminders: list[TaskReminder] = Field(default_factory=list)
    remind_time: datetime | None = Field(default=None, alias="remindTime")

    # Hierarchy (V2 only)
    parent_id: str | None = Field(default=None, alias="parentId")
    child_ids: list[str] | None = Field(default=None, alias="childIds")

    # Checklist items
    items: list[ChecklistItem] = Field(default_factory=list)

    # Organization
    tags: list[str] = Field(default_factory=list)
    column_id: str | None = Field(default=None, alias="columnId")
    sort_order: int | None = Field(default=None, alias="sortOrder")

    # Collaboration (V2 only)
    assignee: Any | None = None
    creator: int | None = None
    completed_user_id: int | None = Field(default=None, alias="completedUserId")
    comment_count: int | None = Field(default=None, alias="commentCount")

    # Attachments (V2 only)
    attachments: list[Any] = Field(default_factory=list)

    # Focus (V2 only)
    focus_summaries: list[Any] = Field(default_factory=list, alias="focusSummaries")
    pomodoro_summaries: list[Any] = Field(default_factory=list, alias="pomodoroSummaries")

    # Validators
    @field_validator(
        "start_date",
        "due_date",
        "created_time",
        "modified_time",
        "completed_time",
        "remind_time",
        "repeat_first_date",
        mode="before",
    )
    @classmethod
    def parse_datetime_field(cls, v: Any) -> datetime | None:
        return cls.parse_datetime(v)

    @field_validator("repeat_from", mode="before")
    @classmethod
    def parse_repeat_from(cls, v: Any) -> int | None:
        if v == "" or v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @field_validator("reminders", mode="before")
    @classmethod
    def parse_reminders(cls, v: Any) -> list[TaskReminder]:
        if v is None:
            return []
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    # V1 format: just the trigger string
                    result.append(TaskReminder(trigger=item))
                elif isinstance(item, dict):
                    # V2 format: dict with id and trigger
                    result.append(TaskReminder.model_validate(item))
                elif isinstance(item, TaskReminder):
                    result.append(item)
            return result
        return []

    @field_validator("items", mode="before")
    @classmethod
    def parse_items(cls, v: Any) -> list[ChecklistItem]:
        if v is None:
            return []
        if isinstance(v, list):
            return [
                ChecklistItem.model_validate(item) if isinstance(item, dict) else item
                for item in v
            ]
        return []

    # Properties
    @property
    def is_completed(self) -> bool:
        """Check if the task is completed."""
        return TaskStatus.is_completed(self.status)

    @property
    def is_closed(self) -> bool:
        """Check if the task is closed (completed or abandoned)."""
        return TaskStatus.is_closed(self.status)

    @property
    def is_abandoned(self) -> bool:
        """Check if the task is abandoned."""
        return self.status == TaskStatus.ABANDONED

    @property
    def is_active(self) -> bool:
        """Check if the task is active."""
        return self.status == TaskStatus.ACTIVE

    @property
    def is_subtask(self) -> bool:
        """Check if this task is a subtask."""
        return self.parent_id is not None

    @property
    def has_subtasks(self) -> bool:
        """Check if this task has subtasks."""
        return bool(self.child_ids)

    @property
    def priority_label(self) -> str:
        """Get human-readable priority label."""
        try:
            return TaskPriority(self.priority).to_string()
        except ValueError:
            return "none"

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
        data: dict[str, Any] = {
            "id": self.id,
            "projectId": self.project_id,
        }

        if self.title is not None:
            data["title"] = self.title
        if self.content is not None:
            data["content"] = self.content
        if self.desc is not None:
            data["desc"] = self.desc
        if self.is_all_day is not None:
            data["isAllDay"] = self.is_all_day
        if self.start_date is not None:
            data["startDate"] = self.format_datetime(self.start_date, "v1")
        if self.due_date is not None:
            data["dueDate"] = self.format_datetime(self.due_date, "v1")
        if self.time_zone is not None:
            data["timeZone"] = self.time_zone
        if self.reminders:
            data["reminders"] = [r.to_v1_string() for r in self.reminders]
        if self.repeat_flag is not None:
            data["repeatFlag"] = self.repeat_flag
        if self.priority is not None:
            data["priority"] = self.priority
        if self.sort_order is not None:
            data["sortOrder"] = self.sort_order
        if self.items:
            data["items"] = [
                item.model_dump(by_alias=True, exclude_none=True)
                for item in self.items
            ]

        return data

    def to_v2_dict(self, for_update: bool = False) -> dict[str, Any]:
        """Convert to V2 API format for requests.

        Args:
            for_update: If True, sends empty strings for None date fields
                       to explicitly clear them. For creates, None means
                       "no value" and is omitted.
        """
        data: dict[str, Any] = {
            "id": self.id,
            "projectId": self.project_id,
        }

        if self.title is not None:
            data["title"] = self.title
        if self.content is not None:
            data["content"] = self.content
        if self.desc is not None:
            data["desc"] = self.desc
        if self.kind is not None:
            data["kind"] = self.kind
        if self.status is not None:
            data["status"] = self.status
        if self.priority is not None:
            data["priority"] = self.priority
        if self.is_all_day is not None:
            data["isAllDay"] = self.is_all_day

        # Date fields: for updates, None means "clear"; for creates, None means "omit"
        if self.start_date is not None:
            data["startDate"] = self.format_datetime(self.start_date, "v2")
        elif for_update:
            data["startDate"] = ""

        if self.due_date is not None:
            data["dueDate"] = self.format_datetime(self.due_date, "v2")
        elif for_update:
            data["dueDate"] = ""

        if self.time_zone is not None:
            data["timeZone"] = self.time_zone
        if self.reminders:
            data["reminders"] = [
                r.model_dump(exclude_none=True) for r in self.reminders
            ]
        if self.repeat_flag is not None:
            data["repeatFlag"] = self.repeat_flag

        # Tags: for updates, always include (empty list clears); for creates, omit if empty
        if self.tags:
            data["tags"] = self.tags
        elif for_update:
            data["tags"] = []

        if self.sort_order is not None:
            data["sortOrder"] = self.sort_order
        if self.items:
            data["items"] = [
                item.model_dump(by_alias=True, exclude_none=True)
                for item in self.items
            ]
        if self.parent_id is not None:
            data["parentId"] = self.parent_id
        if self.completed_time is not None:
            data["completedTime"] = self.format_datetime(self.completed_time, "v2")

        return data

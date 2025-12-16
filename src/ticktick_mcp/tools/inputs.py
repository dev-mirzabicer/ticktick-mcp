"""
Pydantic Input Models for TickTick MCP Tools.

This module defines all input validation models used by MCP tools.
Each model includes proper field constraints, descriptions, and examples.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, field_validator


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


class BaseMCPInput(BaseModel):
    """Base input model with common configuration."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )


# =============================================================================
# Task Input Models
# =============================================================================


class TaskCreateInput(BaseMCPInput):
    """Input for creating a new task."""

    title: str = Field(
        ...,
        description="Task title (e.g., 'Review quarterly report', 'Buy groceries')",
        min_length=1,
        max_length=500,
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Project ID to create the task in. If not provided, uses inbox.",
        pattern=r"^(inbox\d+|[a-f0-9]{24})$",
    )
    content: Optional[str] = Field(
        default=None,
        description="Task notes/content (supports markdown)",
        max_length=10000,
    )
    description: Optional[str] = Field(
        default=None,
        description="Checklist description",
        max_length=5000,
    )
    priority: Optional[str] = Field(
        default=None,
        description="Priority level: 'none' (0), 'low' (1), 'medium' (3), 'high' (5)",
        pattern=r"^(none|low|medium|high|0|1|3|5)$",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Start date in ISO format (e.g., '2025-01-15T09:00:00')",
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Due date in ISO format (e.g., '2025-01-15T17:00:00')",
    )
    all_day: Optional[bool] = Field(
        default=None,
        description="Whether this is an all-day task (no specific time)",
    )
    time_zone: Optional[str] = Field(
        default=None,
        description="IANA timezone (e.g., 'America/New_York', 'UTC')",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="List of tag names to apply (e.g., ['work', 'urgent'])",
        max_length=20,
    )
    reminders: Optional[List[str]] = Field(
        default=None,
        description="Reminder triggers in iCal format (e.g., 'TRIGGER:-PT30M' for 30 min before)",
        max_length=10,
    )
    recurrence: Optional[str] = Field(
        default=None,
        description="Recurrence rule in RRULE format (e.g., 'RRULE:FREQ=DAILY;INTERVAL=1')",
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="Parent task ID to make this a subtask",
        pattern=r"^[a-f0-9]{24}$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable, 'json' for machine-readable",
    )

    @field_validator("priority")
    @classmethod
    def normalize_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # Normalize string priorities to lowercase
        return v.lower()


class TaskGetInput(BaseMCPInput):
    """Input for getting a task by ID."""

    task_id: str = Field(
        ...,
        description="Task identifier (24-character hex string)",
        pattern=r"^[a-f0-9]{24}$",
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Project ID (required for V1 API fallback)",
        pattern=r"^(inbox\d+|[a-f0-9]{24})$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class TaskUpdateInput(BaseMCPInput):
    """Input for updating a task."""

    task_id: str = Field(
        ...,
        description="Task identifier to update",
        pattern=r"^[a-f0-9]{24}$",
    )
    project_id: str = Field(
        ...,
        description="Project ID the task belongs to",
        pattern=r"^(inbox\d+|[a-f0-9]{24})$",
    )
    title: Optional[str] = Field(
        default=None,
        description="New task title",
        min_length=1,
        max_length=500,
    )
    content: Optional[str] = Field(
        default=None,
        description="New task content",
        max_length=10000,
    )
    priority: Optional[str] = Field(
        default=None,
        description="New priority: 'none', 'low', 'medium', 'high'",
        pattern=r"^(none|low|medium|high|0|1|3|5)$",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="New start date in ISO format",
    )
    due_date: Optional[str] = Field(
        default=None,
        description="New due date in ISO format",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="New list of tags (replaces existing)",
        max_length=20,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class TaskCompleteInput(BaseMCPInput):
    """Input for completing a task."""

    task_id: str = Field(
        ...,
        description="Task identifier to complete",
        pattern=r"^[a-f0-9]{24}$",
    )
    project_id: str = Field(
        ...,
        description="Project ID the task belongs to",
        pattern=r"^(inbox\d+|[a-f0-9]{24})$",
    )


class TaskDeleteInput(BaseMCPInput):
    """Input for deleting a task."""

    task_id: str = Field(
        ...,
        description="Task identifier to delete",
        pattern=r"^[a-f0-9]{24}$",
    )
    project_id: str = Field(
        ...,
        description="Project ID the task belongs to",
        pattern=r"^(inbox\d+|[a-f0-9]{24})$",
    )


class TaskMoveInput(BaseMCPInput):
    """Input for moving a task between projects."""

    task_id: str = Field(
        ...,
        description="Task identifier to move",
        pattern=r"^[a-f0-9]{24}$",
    )
    from_project_id: str = Field(
        ...,
        description="Source project ID",
        pattern=r"^(inbox\d+|[a-f0-9]{24})$",
    )
    to_project_id: str = Field(
        ...,
        description="Destination project ID",
        pattern=r"^(inbox\d+|[a-f0-9]{24})$",
    )


class TaskParentInput(BaseMCPInput):
    """Input for setting a task's parent (making it a subtask)."""

    task_id: str = Field(
        ...,
        description="Task identifier to make a subtask",
        pattern=r"^[a-f0-9]{24}$",
    )
    parent_id: str = Field(
        ...,
        description="Parent task identifier",
        pattern=r"^[a-f0-9]{24}$",
    )
    project_id: str = Field(
        ...,
        description="Project ID containing both tasks",
        pattern=r"^(inbox\d+|[a-f0-9]{24})$",
    )


class TaskListInput(BaseMCPInput):
    """Input for listing tasks."""

    project_id: Optional[str] = Field(
        default=None,
        description="Filter by project ID. If not provided, returns all tasks.",
        pattern=r"^(inbox\d+|[a-f0-9]{24})$",
    )
    tag: Optional[str] = Field(
        default=None,
        description="Filter by tag name",
    )
    priority: Optional[str] = Field(
        default=None,
        description="Filter by priority: 'none', 'low', 'medium', 'high'",
        pattern=r"^(none|low|medium|high)$",
    )
    due_today: Optional[bool] = Field(
        default=None,
        description="Filter to only tasks due today",
    )
    overdue: Optional[bool] = Field(
        default=None,
        description="Filter to only overdue tasks",
    )
    limit: int = Field(
        default=50,
        description="Maximum number of tasks to return",
        ge=1,
        le=500,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class CompletedTasksInput(BaseMCPInput):
    """Input for listing completed tasks."""

    days: int = Field(
        default=7,
        description="Number of days to look back",
        ge=1,
        le=90,
    )
    limit: int = Field(
        default=50,
        description="Maximum number of tasks to return",
        ge=1,
        le=200,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


# =============================================================================
# Project Input Models
# =============================================================================


class ProjectCreateInput(BaseMCPInput):
    """Input for creating a project."""

    name: str = Field(
        ...,
        description="Project name (e.g., 'Work', 'Personal', 'Shopping')",
        min_length=1,
        max_length=100,
    )
    color: Optional[str] = Field(
        default=None,
        description="Hex color code (e.g., '#F18181', '#86BB6D')",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )
    kind: Optional[str] = Field(
        default="TASK",
        description="Project type: 'TASK' for tasks, 'NOTE' for notes",
        pattern=r"^(TASK|NOTE)$",
    )
    view_mode: Optional[str] = Field(
        default="list",
        description="View mode: 'list', 'kanban', 'timeline'",
        pattern=r"^(list|kanban|timeline)$",
    )
    folder_id: Optional[str] = Field(
        default=None,
        description="Parent folder ID to place project in",
        pattern=r"^[a-f0-9]{24}$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class ProjectGetInput(BaseMCPInput):
    """Input for getting a project."""

    project_id: str = Field(
        ...,
        description="Project identifier",
        pattern=r"^(inbox\d+|[a-f0-9]{24})$",
    )
    include_tasks: bool = Field(
        default=False,
        description="Whether to include tasks in the response",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class ProjectDeleteInput(BaseMCPInput):
    """Input for deleting a project."""

    project_id: str = Field(
        ...,
        description="Project identifier to delete",
        pattern=r"^[a-f0-9]{24}$",
    )


# =============================================================================
# Folder Input Models
# =============================================================================


class FolderCreateInput(BaseMCPInput):
    """Input for creating a folder (project group)."""

    name: str = Field(
        ...,
        description="Folder name",
        min_length=1,
        max_length=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class FolderDeleteInput(BaseMCPInput):
    """Input for deleting a folder."""

    folder_id: str = Field(
        ...,
        description="Folder identifier to delete",
        pattern=r"^[a-f0-9]{24}$",
    )


# =============================================================================
# Tag Input Models
# =============================================================================


class TagCreateInput(BaseMCPInput):
    """Input for creating a tag."""

    name: str = Field(
        ...,
        description="Tag name/label (e.g., 'work', 'personal', 'urgent')",
        min_length=1,
        max_length=50,
    )
    color: Optional[str] = Field(
        default=None,
        description="Hex color code (e.g., '#F18181')",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )
    parent: Optional[str] = Field(
        default=None,
        description="Parent tag name for nesting",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


class TagDeleteInput(BaseMCPInput):
    """Input for deleting a tag."""

    name: str = Field(
        ...,
        description="Tag name to delete (lowercase identifier)",
        min_length=1,
        max_length=50,
    )


class TagRenameInput(BaseMCPInput):
    """Input for renaming a tag."""

    old_name: str = Field(
        ...,
        description="Current tag name",
        min_length=1,
        max_length=50,
    )
    new_name: str = Field(
        ...,
        description="New tag name",
        min_length=1,
        max_length=50,
    )


class TagMergeInput(BaseMCPInput):
    """Input for merging tags."""

    source: str = Field(
        ...,
        description="Tag to merge from (will be deleted)",
        min_length=1,
        max_length=50,
    )
    target: str = Field(
        ...,
        description="Tag to merge into (will remain)",
        min_length=1,
        max_length=50,
    )


# =============================================================================
# Focus/Pomodoro Input Models
# =============================================================================


class FocusStatsInput(BaseMCPInput):
    """Input for focus/pomodoro statistics."""

    start_date: Optional[str] = Field(
        default=None,
        description="Start date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="End date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    days: int = Field(
        default=30,
        description="Number of days to look back (if dates not specified)",
        ge=1,
        le=365,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )


# =============================================================================
# Search Input Model
# =============================================================================


class SearchInput(BaseMCPInput):
    """Input for searching tasks."""

    query: str = Field(
        ...,
        description="Search query to match against task titles and content",
        min_length=1,
        max_length=200,
    )
    limit: int = Field(
        default=20,
        description="Maximum number of results to return",
        ge=1,
        le=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()

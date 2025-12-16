"""
Type definitions for TickTick V1 API.

These TypedDicts represent the exact JSON structures used in V1 API
requests and responses.
"""

from __future__ import annotations

from typing import TypedDict, NotRequired


# =============================================================================
# Checklist Item (Subtask)
# =============================================================================


class ChecklistItemV1(TypedDict):
    """V1 API checklist/subtask item."""

    id: str
    title: NotRequired[str]
    status: NotRequired[int]  # 0 = normal, 1 = completed
    completedTime: NotRequired[str]  # ISO datetime
    isAllDay: NotRequired[bool]
    sortOrder: NotRequired[int]
    startDate: NotRequired[str]  # ISO datetime
    timeZone: NotRequired[str]


class ChecklistItemCreateV1(TypedDict, total=False):
    """V1 API checklist item for creation."""

    title: str
    status: int
    isAllDay: bool
    sortOrder: int
    startDate: str
    timeZone: str
    completedTime: str


# =============================================================================
# Task
# =============================================================================


class TaskV1(TypedDict):
    """V1 API task response."""

    id: str
    projectId: str
    title: NotRequired[str]
    content: NotRequired[str]
    desc: NotRequired[str]
    isAllDay: NotRequired[bool]
    startDate: NotRequired[str]  # ISO datetime
    dueDate: NotRequired[str]  # ISO datetime
    timeZone: NotRequired[str]
    reminders: NotRequired[list[str]]  # TRIGGER format
    repeatFlag: NotRequired[str]  # RRULE format
    priority: NotRequired[int]  # 0, 1, 3, 5
    status: NotRequired[int]  # 0 = active, 2 = completed
    completedTime: NotRequired[str]  # ISO datetime
    sortOrder: NotRequired[int]
    items: NotRequired[list[ChecklistItemV1]]
    kind: NotRequired[str]  # TEXT, NOTE, CHECKLIST


class TaskCreateV1(TypedDict, total=False):
    """V1 API task creation request."""

    title: str  # Required
    projectId: str  # Required
    content: str
    desc: str
    isAllDay: bool
    startDate: str
    dueDate: str
    timeZone: str
    reminders: list[str]
    repeatFlag: str
    priority: int
    sortOrder: int
    items: list[ChecklistItemCreateV1]


class TaskUpdateV1(TypedDict, total=False):
    """V1 API task update request."""

    id: str  # Required
    projectId: str  # Required
    title: str
    content: str
    desc: str
    isAllDay: bool
    startDate: str
    dueDate: str
    timeZone: str
    reminders: list[str]
    repeatFlag: str
    priority: int
    sortOrder: int
    items: list[ChecklistItemV1]


# =============================================================================
# Project
# =============================================================================


class ProjectV1(TypedDict):
    """V1 API project response."""

    id: str
    name: str
    color: NotRequired[str]
    sortOrder: NotRequired[int]
    closed: NotRequired[bool]
    groupId: NotRequired[str]
    viewMode: NotRequired[str]  # list, kanban, timeline
    permission: NotRequired[str]  # read, write, comment
    kind: NotRequired[str]  # TASK, NOTE


class ProjectCreateV1(TypedDict, total=False):
    """V1 API project creation request."""

    name: str  # Required
    color: str
    sortOrder: int
    viewMode: str
    kind: str


class ProjectUpdateV1(TypedDict, total=False):
    """V1 API project update request."""

    name: str
    color: str
    sortOrder: int
    viewMode: str
    kind: str


# =============================================================================
# Column (Kanban)
# =============================================================================


class ColumnV1(TypedDict):
    """V1 API kanban column."""

    id: str
    projectId: str
    name: str
    sortOrder: NotRequired[int]


# =============================================================================
# Project Data (with tasks and columns)
# =============================================================================


class ProjectDataV1(TypedDict):
    """V1 API project with data response."""

    project: ProjectV1
    tasks: list[TaskV1]
    columns: NotRequired[list[ColumnV1]]

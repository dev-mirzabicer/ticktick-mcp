"""
TickTick Unified Data Models.

This package provides canonical Pydantic models that unify V1 and V2 API
data structures. These models are the single source of truth for the
TickTick MCP server.

Models:
    - Task: Unified task model
    - Project: Unified project model
    - ProjectGroup: Project folder/group
    - Tag: Tag model
    - ChecklistItem: Subtask/checklist item
    - Column: Kanban column
    - User: User profile and status
    - FocusStats: Focus/Pomodoro statistics
"""

from ticktick_mcp.models.task import Task, ChecklistItem, TaskReminder
from ticktick_mcp.models.project import Project, ProjectGroup, Column, ProjectData
from ticktick_mcp.models.tag import Tag
from ticktick_mcp.models.user import User, UserStatus, UserStatistics

__all__ = [
    "Task",
    "ChecklistItem",
    "TaskReminder",
    "Project",
    "ProjectGroup",
    "Column",
    "ProjectData",
    "Tag",
    "User",
    "UserStatus",
    "UserStatistics",
]

"""
TickTick MCP Tools Package.

This package provides all MCP tool definitions for the TickTick MCP server.
Tools are organized into logical groups:
    - Task tools (create, read, update, delete, complete, move, etc.)
    - Project tools (CRUD, get with data)
    - Tag tools (CRUD, rename, merge)
    - User tools (profile, status, statistics)
    - Focus tools (heatmap, distribution)
    - Sync tools (full state sync)
"""

from ticktick_mcp.tools.inputs import (
    ResponseFormat,
    TaskCreateInput,
    TaskGetInput,
    TaskUpdateInput,
    TaskCompleteInput,
    TaskDeleteInput,
    TaskMoveInput,
    TaskParentInput,
    TaskListInput,
    CompletedTasksInput,
    ProjectCreateInput,
    ProjectGetInput,
    ProjectDeleteInput,
    FolderCreateInput,
    FolderDeleteInput,
    TagCreateInput,
    TagDeleteInput,
    TagRenameInput,
    TagMergeInput,
    FocusStatsInput,
    SearchInput,
)

__all__ = [
    "ResponseFormat",
    "TaskCreateInput",
    "TaskGetInput",
    "TaskUpdateInput",
    "TaskCompleteInput",
    "TaskDeleteInput",
    "TaskMoveInput",
    "TaskParentInput",
    "TaskListInput",
    "CompletedTasksInput",
    "ProjectCreateInput",
    "ProjectGetInput",
    "ProjectDeleteInput",
    "FolderCreateInput",
    "FolderDeleteInput",
    "TagCreateInput",
    "TagDeleteInput",
    "TagRenameInput",
    "TagMergeInput",
    "FocusStatsInput",
    "SearchInput",
]

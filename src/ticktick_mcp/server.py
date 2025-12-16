#!/usr/bin/env python3
"""
TickTick MCP Server.

This server provides comprehensive tools for interacting with TickTick,
combining both V1 (OAuth2) and V2 (Session) APIs for maximum functionality.

Features:
    - Task management (create, read, update, delete, complete, move)
    - Project management (CRUD, folders)
    - Tag management (CRUD, rename, merge)
    - User information (profile, status, statistics)
    - Focus/Pomodoro tracking
    - Full state sync

Environment Variables Required:
    V1 (OAuth2):
        TICKTICK_CLIENT_ID
        TICKTICK_CLIENT_SECRET
        TICKTICK_ACCESS_TOKEN

    V2 (Session):
        TICKTICK_USERNAME
        TICKTICK_PASSWORD
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Any, AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

from ticktick_mcp.client import TickTickClient
from ticktick_mcp.settings import get_settings
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
from ticktick_mcp.tools.formatting import (
    format_task_markdown,
    format_task_json,
    format_tasks_markdown,
    format_tasks_json,
    format_project_markdown,
    format_project_json,
    format_projects_markdown,
    format_projects_json,
    format_tag_markdown,
    format_tag_json,
    format_tags_markdown,
    format_tags_json,
    format_folders_markdown,
    format_folders_json,
    format_user_markdown,
    format_user_status_markdown,
    format_statistics_markdown,
    format_response,
    success_message,
    error_message,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan Management
# =============================================================================


@asynccontextmanager
async def lifespan(mcp: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """
    Manage the TickTick client lifecycle.

    Initializes the client on startup and closes it on shutdown.
    """
    logger.info("Initializing TickTick MCP Server...")

    try:
        client = TickTickClient.from_settings()
        await client.connect()
        logger.info("TickTick client connected successfully")
        yield {"client": client}
    except Exception as e:
        logger.error("Failed to initialize TickTick client: %s", e)
        raise
    finally:
        if "client" in locals():
            await client.disconnect()
            logger.info("TickTick client disconnected")


# Initialize FastMCP server
mcp = FastMCP(
    "ticktick_mcp",
    lifespan=lifespan,
)


def get_client(ctx: Context) -> TickTickClient:
    """Get the TickTick client from context."""
    return ctx.request_context.lifespan_state["client"]


# =============================================================================
# Error Handling
# =============================================================================


def handle_error(e: Exception, operation: str) -> str:
    """Handle exceptions and return user-friendly error messages."""
    logger.exception("Error in %s: %s", operation, e)

    error_type = type(e).__name__

    if "Authentication" in error_type:
        return error_message(
            "Authentication failed. Please check your credentials.",
            "Ensure TICKTICK_CLIENT_ID, TICKTICK_CLIENT_SECRET, TICKTICK_ACCESS_TOKEN, "
            "TICKTICK_USERNAME, and TICKTICK_PASSWORD are set correctly.",
        )
    elif "NotFound" in error_type:
        return error_message(
            f"Resource not found: {e}",
            "Verify the ID is correct and the resource exists.",
        )
    elif "Validation" in error_type:
        return error_message(f"Invalid input: {e}")
    elif "Configuration" in error_type:
        return error_message(
            f"Configuration error: {e}",
            "Check your environment variables and settings.",
        )
    else:
        return error_message(f"Unexpected error: {e}")


# =============================================================================
# Task Tools
# =============================================================================


@mcp.tool(
    name="ticktick_create_task",
    annotations={
        "title": "Create Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def ticktick_create_task(params: TaskCreateInput, ctx: Context) -> str:
    """
    Create a new task in TickTick.

    This tool creates a new task with the specified properties. Tasks can include
    titles, due dates, priorities, tags, reminders, and recurrence rules.

    Args:
        params: Task creation parameters including:
            - title (str): Task title (required)
            - project_id (str): Project to create in (defaults to inbox)
            - content (str): Task notes/description
            - priority (str): 'none', 'low', 'medium', 'high'
            - due_date (str): Due date in ISO format
            - tags (list): Tag names to apply
            - reminders (list): Reminder triggers
            - recurrence (str): RRULE for recurring tasks

    Returns:
        Formatted task details on success, or error message on failure.

    Examples:
        - Create simple task: title="Buy groceries"
        - Create with due date: title="Submit report", due_date="2025-01-20T17:00:00"
        - Create with tags: title="Meeting", tags=["work", "important"], priority="high"
    """
    try:
        client = get_client(ctx)

        # Parse priority
        priority = None
        if params.priority:
            priority_map = {"none": 0, "low": 1, "medium": 3, "high": 5, "0": 0, "1": 1, "3": 3, "5": 5}
            priority = priority_map.get(params.priority, 0)

        # Parse dates
        start_date = datetime.fromisoformat(params.start_date) if params.start_date else None
        due_date = datetime.fromisoformat(params.due_date) if params.due_date else None

        task = await client.create_task(
            title=params.title,
            project_id=params.project_id,
            content=params.content,
            description=params.description,
            priority=priority,
            start_date=start_date,
            due_date=due_date,
            time_zone=params.time_zone,
            all_day=params.all_day,
            tags=params.tags,
            reminders=params.reminders,
            recurrence=params.recurrence,
            parent_id=params.parent_id,
        )

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Task Created\n\n{format_task_markdown(task)}"
        else:
            return json.dumps({"success": True, "task": format_task_json(task)}, indent=2)

    except Exception as e:
        return handle_error(e, "create_task")


@mcp.tool(
    name="ticktick_get_task",
    annotations={
        "title": "Get Task",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_get_task(params: TaskGetInput, ctx: Context) -> str:
    """
    Get a task by its ID.

    Retrieves full details of a specific task including title, description,
    due date, priority, tags, subtasks, and completion status.

    Args:
        params: Query parameters including:
            - task_id (str): Task identifier (required)
            - project_id (str): Project ID (needed for V1 fallback)

    Returns:
        Formatted task details or error message.
    """
    try:
        client = get_client(ctx)
        task = await client.get_task(params.task_id, params.project_id)

        if params.response_format == ResponseFormat.MARKDOWN:
            return format_task_markdown(task)
        else:
            return json.dumps(format_task_json(task), indent=2)

    except Exception as e:
        return handle_error(e, "get_task")


@mcp.tool(
    name="ticktick_list_tasks",
    annotations={
        "title": "List Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_list_tasks(params: TaskListInput, ctx: Context) -> str:
    """
    List tasks with optional filters.

    Retrieves active tasks, optionally filtered by project, tag, priority,
    or due date. Returns tasks sorted by due date and priority.

    Args:
        params: Filter parameters including:
            - project_id (str): Filter by project
            - tag (str): Filter by tag name
            - priority (str): Filter by priority level
            - due_today (bool): Only tasks due today
            - overdue (bool): Only overdue tasks
            - limit (int): Maximum results (default 50)

    Returns:
        Formatted list of tasks or error message.

    Examples:
        - List all tasks: (no filters)
        - List by project: project_id="60caa20d..."
        - List urgent: priority="high"
        - List overdue: overdue=True
    """
    try:
        client = get_client(ctx)
        tasks = await client.get_all_tasks()

        # Apply filters
        if params.project_id:
            tasks = [t for t in tasks if t.project_id == params.project_id]

        if params.tag:
            tag_lower = params.tag.lower()
            tasks = [t for t in tasks if any(tag.lower() == tag_lower for tag in t.tags)]

        if params.priority:
            priority_map = {"none": 0, "low": 1, "medium": 3, "high": 5}
            target_priority = priority_map.get(params.priority, 0)
            tasks = [t for t in tasks if t.priority == target_priority]

        if params.due_today:
            today = date.today()
            tasks = [t for t in tasks if t.due_date and t.due_date.date() == today]

        if params.overdue:
            today = date.today()
            tasks = [t for t in tasks if t.due_date and t.due_date.date() < today and not t.is_completed]

        # Apply limit
        tasks = tasks[: params.limit]

        if params.response_format == ResponseFormat.MARKDOWN:
            return format_tasks_markdown(tasks)
        else:
            return json.dumps(format_tasks_json(tasks), indent=2)

    except Exception as e:
        return handle_error(e, "list_tasks")


@mcp.tool(
    name="ticktick_update_task",
    annotations={
        "title": "Update Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_update_task(params: TaskUpdateInput, ctx: Context) -> str:
    """
    Update an existing task.

    Updates specified fields of a task while preserving others.

    Args:
        params: Update parameters including:
            - task_id (str): Task to update (required)
            - project_id (str): Project containing the task (required)
            - title (str): New title
            - content (str): New content/notes
            - priority (str): New priority
            - due_date (str): New due date
            - tags (list): New tags (replaces existing)

    Returns:
        Updated task details or error message.

    Examples:
        - Update title: task_id="...", project_id="...", title="New Title"
        - Update priority: task_id="...", project_id="...", priority="high"
    """
    try:
        client = get_client(ctx)

        # Get existing task
        task = await client.get_task(params.task_id, params.project_id)

        # Update fields if provided
        if params.title is not None:
            task.title = params.title
        if params.content is not None:
            task.content = params.content
        if params.priority is not None:
            priority_map = {"none": 0, "low": 1, "medium": 3, "high": 5, "0": 0, "1": 1, "3": 3, "5": 5}
            task.priority = priority_map.get(params.priority, task.priority)
        if params.start_date is not None:
            task.start_date = datetime.fromisoformat(params.start_date)
        if params.due_date is not None:
            task.due_date = datetime.fromisoformat(params.due_date)
        if params.tags is not None:
            task.tags = params.tags

        # Save updates
        updated_task = await client.update_task(task)

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Task Updated\n\n{format_task_markdown(updated_task)}"
        else:
            return json.dumps({"success": True, "task": format_task_json(updated_task)}, indent=2)

    except Exception as e:
        return handle_error(e, "update_task")


@mcp.tool(
    name="ticktick_complete_task",
    annotations={
        "title": "Complete Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_complete_task(params: TaskCompleteInput, ctx: Context) -> str:
    """
    Mark a task as complete.

    Changes the task status to completed and records the completion time.
    This operation is idempotent - completing an already-completed task
    has no additional effect.

    Args:
        params: Completion parameters:
            - task_id (str): Task to complete (required)
            - project_id (str): Project containing the task (required)

    Returns:
        Success confirmation or error message.
    """
    try:
        client = get_client(ctx)
        await client.complete_task(params.task_id, params.project_id)
        return success_message(f"Task `{params.task_id}` marked as complete.")

    except Exception as e:
        return handle_error(e, "complete_task")


@mcp.tool(
    name="ticktick_delete_task",
    annotations={
        "title": "Delete Task",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_delete_task(params: TaskDeleteInput, ctx: Context) -> str:
    """
    Delete a task.

    Moves the task to trash. This is a destructive operation but can be
    undone from the TickTick trash.

    Args:
        params: Deletion parameters:
            - task_id (str): Task to delete (required)
            - project_id (str): Project containing the task (required)

    Returns:
        Success confirmation or error message.
    """
    try:
        client = get_client(ctx)
        await client.delete_task(params.task_id, params.project_id)
        return success_message(f"Task `{params.task_id}` deleted.")

    except Exception as e:
        return handle_error(e, "delete_task")


@mcp.tool(
    name="ticktick_move_task",
    annotations={
        "title": "Move Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_move_task(params: TaskMoveInput, ctx: Context) -> str:
    """
    Move a task to a different project.

    Transfers a task from one project to another while preserving
    all task properties.

    Args:
        params: Move parameters:
            - task_id (str): Task to move (required)
            - from_project_id (str): Source project (required)
            - to_project_id (str): Destination project (required)

    Returns:
        Success confirmation or error message.
    """
    try:
        client = get_client(ctx)
        await client.move_task(params.task_id, params.from_project_id, params.to_project_id)
        return success_message(f"Task `{params.task_id}` moved to project `{params.to_project_id}`.")

    except Exception as e:
        return handle_error(e, "move_task")


@mcp.tool(
    name="ticktick_make_subtask",
    annotations={
        "title": "Make Subtask",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_make_subtask(params: TaskParentInput, ctx: Context) -> str:
    """
    Make a task a subtask of another task.

    Creates a parent-child relationship between two tasks. The child task
    will appear nested under the parent task.

    Args:
        params: Parent assignment parameters:
            - task_id (str): Task to make a subtask (required)
            - parent_id (str): Parent task ID (required)
            - project_id (str): Project containing both tasks (required)

    Returns:
        Success confirmation or error message.
    """
    try:
        client = get_client(ctx)
        await client.make_subtask(params.task_id, params.parent_id, params.project_id)
        return success_message(f"Task `{params.task_id}` is now a subtask of `{params.parent_id}`.")

    except Exception as e:
        return handle_error(e, "make_subtask")


@mcp.tool(
    name="ticktick_completed_tasks",
    annotations={
        "title": "Get Completed Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_completed_tasks(params: CompletedTasksInput, ctx: Context) -> str:
    """
    Get recently completed tasks.

    Retrieves tasks that were completed within the specified time period.
    Useful for reviewing productivity and completed work.

    Args:
        params: Query parameters:
            - days (int): Number of days to look back (default 7)
            - limit (int): Maximum results (default 50)

    Returns:
        Formatted list of completed tasks or error message.
    """
    try:
        client = get_client(ctx)
        tasks = await client.get_completed_tasks(days=params.days, limit=params.limit)

        title = f"Completed Tasks (Last {params.days} Days)"

        if params.response_format == ResponseFormat.MARKDOWN:
            return format_tasks_markdown(tasks, title)
        else:
            return json.dumps(format_tasks_json(tasks), indent=2)

    except Exception as e:
        return handle_error(e, "completed_tasks")


@mcp.tool(
    name="ticktick_search_tasks",
    annotations={
        "title": "Search Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_search_tasks(params: SearchInput, ctx: Context) -> str:
    """
    Search for tasks by title or content.

    Performs a text search across all active tasks, matching the query
    against task titles and content.

    Args:
        params: Search parameters:
            - query (str): Search query (required)
            - limit (int): Maximum results (default 20)

    Returns:
        Formatted list of matching tasks or error message.

    Examples:
        - Search by keyword: query="meeting"
        - Search by phrase: query="quarterly report"
    """
    try:
        client = get_client(ctx)
        tasks = await client.search_tasks(params.query)
        tasks = tasks[: params.limit]

        title = f"Search Results: '{params.query}'"

        if params.response_format == ResponseFormat.MARKDOWN:
            return format_tasks_markdown(tasks, title)
        else:
            return json.dumps(format_tasks_json(tasks), indent=2)

    except Exception as e:
        return handle_error(e, "search_tasks")


# =============================================================================
# Project Tools
# =============================================================================


@mcp.tool(
    name="ticktick_list_projects",
    annotations={
        "title": "List Projects",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_list_projects(ctx: Context, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """
    List all projects.

    Retrieves all user projects including their IDs, names, colors,
    and organization settings.

    Returns:
        Formatted list of projects or error message.
    """
    try:
        client = get_client(ctx)
        projects = await client.get_all_projects()

        if response_format == ResponseFormat.MARKDOWN:
            return format_projects_markdown(projects)
        else:
            return json.dumps(format_projects_json(projects), indent=2)

    except Exception as e:
        return handle_error(e, "list_projects")


@mcp.tool(
    name="ticktick_get_project",
    annotations={
        "title": "Get Project",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_get_project(params: ProjectGetInput, ctx: Context) -> str:
    """
    Get a project by ID, optionally with its tasks.

    Retrieves project details and optionally all tasks within the project.

    Args:
        params: Query parameters:
            - project_id (str): Project identifier (required)
            - include_tasks (bool): Include project tasks (default False)

    Returns:
        Formatted project details or error message.
    """
    try:
        client = get_client(ctx)

        if params.include_tasks:
            project_data = await client.get_project_tasks(params.project_id)

            if params.response_format == ResponseFormat.MARKDOWN:
                lines = [format_project_markdown(project_data.project)]
                lines.append("")
                lines.append(format_tasks_markdown(project_data.tasks, "Tasks"))
                return "\n".join(lines)
            else:
                return json.dumps({
                    "project": format_project_json(project_data.project),
                    "tasks": format_tasks_json(project_data.tasks),
                }, indent=2)
        else:
            project = await client.get_project(params.project_id)

            if params.response_format == ResponseFormat.MARKDOWN:
                return format_project_markdown(project)
            else:
                return json.dumps(format_project_json(project), indent=2)

    except Exception as e:
        return handle_error(e, "get_project")


@mcp.tool(
    name="ticktick_create_project",
    annotations={
        "title": "Create Project",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def ticktick_create_project(params: ProjectCreateInput, ctx: Context) -> str:
    """
    Create a new project.

    Creates a new project/list for organizing tasks. Projects can have
    different view modes and be organized in folders.

    Args:
        params: Project creation parameters:
            - name (str): Project name (required)
            - color (str): Hex color code (e.g., '#F18181')
            - kind (str): 'TASK' or 'NOTE'
            - view_mode (str): 'list', 'kanban', or 'timeline'
            - folder_id (str): Parent folder ID

    Returns:
        Formatted project details or error message.
    """
    try:
        client = get_client(ctx)

        project = await client.create_project(
            name=params.name,
            color=params.color,
            kind=params.kind,
            view_mode=params.view_mode,
            folder_id=params.folder_id,
        )

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Project Created\n\n{format_project_markdown(project)}"
        else:
            return json.dumps({"success": True, "project": format_project_json(project)}, indent=2)

    except Exception as e:
        return handle_error(e, "create_project")


@mcp.tool(
    name="ticktick_delete_project",
    annotations={
        "title": "Delete Project",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_delete_project(params: ProjectDeleteInput, ctx: Context) -> str:
    """
    Delete a project.

    Permanently deletes a project and all its tasks. This is a destructive
    operation that cannot be undone.

    Args:
        params: Deletion parameters:
            - project_id (str): Project to delete (required)

    Returns:
        Success confirmation or error message.
    """
    try:
        client = get_client(ctx)
        await client.delete_project(params.project_id)
        return success_message(f"Project `{params.project_id}` deleted.")

    except Exception as e:
        return handle_error(e, "delete_project")


# =============================================================================
# Folder Tools
# =============================================================================


@mcp.tool(
    name="ticktick_list_folders",
    annotations={
        "title": "List Folders",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_list_folders(ctx: Context, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """
    List all folders (project groups).

    Retrieves all folders used to organize projects.

    Returns:
        Formatted list of folders or error message.
    """
    try:
        client = get_client(ctx)
        folders = await client.get_all_folders()

        if response_format == ResponseFormat.MARKDOWN:
            return format_folders_markdown(folders)
        else:
            return json.dumps(format_folders_json(folders), indent=2)

    except Exception as e:
        return handle_error(e, "list_folders")


@mcp.tool(
    name="ticktick_create_folder",
    annotations={
        "title": "Create Folder",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def ticktick_create_folder(params: FolderCreateInput, ctx: Context) -> str:
    """
    Create a new folder for organizing projects.

    Args:
        params: Folder creation parameters:
            - name (str): Folder name (required)

    Returns:
        Formatted folder details or error message.
    """
    try:
        client = get_client(ctx)
        folder = await client.create_folder(params.name)

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Folder Created\n\n- **{folder.name}** (`{folder.id}`)"
        else:
            return json.dumps({"success": True, "folder": {"id": folder.id, "name": folder.name}}, indent=2)

    except Exception as e:
        return handle_error(e, "create_folder")


@mcp.tool(
    name="ticktick_delete_folder",
    annotations={
        "title": "Delete Folder",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_delete_folder(params: FolderDeleteInput, ctx: Context) -> str:
    """
    Delete a folder.

    Deletes a folder. Projects in the folder are not deleted but become
    ungrouped.

    Args:
        params: Deletion parameters:
            - folder_id (str): Folder to delete (required)

    Returns:
        Success confirmation or error message.
    """
    try:
        client = get_client(ctx)
        await client.delete_folder(params.folder_id)
        return success_message(f"Folder `{params.folder_id}` deleted.")

    except Exception as e:
        return handle_error(e, "delete_folder")


# =============================================================================
# Tag Tools
# =============================================================================


@mcp.tool(
    name="ticktick_list_tags",
    annotations={
        "title": "List Tags",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_list_tags(ctx: Context, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """
    List all tags.

    Retrieves all tags with their colors and hierarchy.

    Returns:
        Formatted list of tags or error message.
    """
    try:
        client = get_client(ctx)
        tags = await client.get_all_tags()

        if response_format == ResponseFormat.MARKDOWN:
            return format_tags_markdown(tags)
        else:
            return json.dumps(format_tags_json(tags), indent=2)

    except Exception as e:
        return handle_error(e, "list_tags")


@mcp.tool(
    name="ticktick_create_tag",
    annotations={
        "title": "Create Tag",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def ticktick_create_tag(params: TagCreateInput, ctx: Context) -> str:
    """
    Create a new tag.

    Tags are used to categorize and filter tasks across projects.

    Args:
        params: Tag creation parameters:
            - name (str): Tag name (required)
            - color (str): Hex color code
            - parent (str): Parent tag name for nesting

    Returns:
        Formatted tag details or error message.
    """
    try:
        client = get_client(ctx)
        tag = await client.create_tag(params.name, color=params.color, parent=params.parent)

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Tag Created\n\n{format_tag_markdown(tag)}"
        else:
            return json.dumps({"success": True, "tag": format_tag_json(tag)}, indent=2)

    except Exception as e:
        return handle_error(e, "create_tag")


@mcp.tool(
    name="ticktick_delete_tag",
    annotations={
        "title": "Delete Tag",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_delete_tag(params: TagDeleteInput, ctx: Context) -> str:
    """
    Delete a tag.

    Removes the tag. Tasks with this tag will no longer have it.

    Args:
        params: Deletion parameters:
            - name (str): Tag name to delete (required)

    Returns:
        Success confirmation or error message.
    """
    try:
        client = get_client(ctx)
        await client.delete_tag(params.name)
        return success_message(f"Tag `{params.name}` deleted.")

    except Exception as e:
        return handle_error(e, "delete_tag")


@mcp.tool(
    name="ticktick_rename_tag",
    annotations={
        "title": "Rename Tag",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_rename_tag(params: TagRenameInput, ctx: Context) -> str:
    """
    Rename a tag.

    Changes the tag name while preserving all task associations.

    Args:
        params: Rename parameters:
            - old_name (str): Current tag name (required)
            - new_name (str): New tag name (required)

    Returns:
        Success confirmation or error message.
    """
    try:
        client = get_client(ctx)
        await client.rename_tag(params.old_name, params.new_name)
        return success_message(f"Tag `{params.old_name}` renamed to `{params.new_name}`.")

    except Exception as e:
        return handle_error(e, "rename_tag")


@mcp.tool(
    name="ticktick_merge_tags",
    annotations={
        "title": "Merge Tags",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_merge_tags(params: TagMergeInput, ctx: Context) -> str:
    """
    Merge one tag into another.

    Moves all tasks from the source tag to the target tag, then deletes
    the source tag.

    Args:
        params: Merge parameters:
            - source (str): Tag to merge from (will be deleted)
            - target (str): Tag to merge into (will remain)

    Returns:
        Success confirmation or error message.
    """
    try:
        client = get_client(ctx)
        await client.merge_tags(params.source, params.target)
        return success_message(f"Tag `{params.source}` merged into `{params.target}`.")

    except Exception as e:
        return handle_error(e, "merge_tags")


# =============================================================================
# User Tools
# =============================================================================


@mcp.tool(
    name="ticktick_get_profile",
    annotations={
        "title": "Get User Profile",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_get_profile(ctx: Context, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """
    Get user profile information.

    Retrieves the current user's profile including username, display name,
    and account settings.

    Returns:
        Formatted user profile or error message.
    """
    try:
        client = get_client(ctx)
        user = await client.get_profile()

        if response_format == ResponseFormat.MARKDOWN:
            return format_user_markdown(user)
        else:
            return json.dumps({
                "username": user.username,
                "display_name": user.display_name,
                "name": user.name,
                "email": user.email,
                "locale": user.locale,
                "verified_email": user.verified_email,
            }, indent=2)

    except Exception as e:
        return handle_error(e, "get_profile")


@mcp.tool(
    name="ticktick_get_status",
    annotations={
        "title": "Get Account Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_get_status(ctx: Context, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """
    Get account status and subscription information.

    Retrieves subscription status, Pro account details, and team membership.

    Returns:
        Formatted account status or error message.
    """
    try:
        client = get_client(ctx)
        status = await client.get_status()

        if response_format == ResponseFormat.MARKDOWN:
            return format_user_status_markdown(status)
        else:
            return json.dumps({
                "user_id": status.user_id,
                "username": status.username,
                "inbox_id": status.inbox_id,
                "is_pro": status.is_pro,
                "pro_end_date": status.pro_end_date,
                "team_user": status.team_user,
            }, indent=2)

    except Exception as e:
        return handle_error(e, "get_status")


@mcp.tool(
    name="ticktick_get_statistics",
    annotations={
        "title": "Get Productivity Statistics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_get_statistics(ctx: Context, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """
    Get productivity statistics.

    Retrieves task completion statistics, scores, levels, and focus/pomodoro data.

    Returns:
        Formatted statistics or error message.
    """
    try:
        client = get_client(ctx)
        stats = await client.get_statistics()

        if response_format == ResponseFormat.MARKDOWN:
            return format_statistics_markdown(stats)
        else:
            return json.dumps({
                "level": stats.level,
                "score": stats.score,
                "today_completed": stats.today_completed,
                "yesterday_completed": stats.yesterday_completed,
                "total_completed": stats.total_completed,
                "today_pomo_count": stats.today_pomo_count,
                "total_pomo_count": stats.total_pomo_count,
                "total_pomo_duration_hours": stats.total_pomo_duration_hours,
            }, indent=2)

    except Exception as e:
        return handle_error(e, "get_statistics")


# =============================================================================
# Focus Tools
# =============================================================================


@mcp.tool(
    name="ticktick_focus_heatmap",
    annotations={
        "title": "Get Focus Heatmap",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_focus_heatmap(params: FocusStatsInput, ctx: Context) -> str:
    """
    Get focus/pomodoro heatmap data.

    Retrieves focus time data for visualization as a heatmap.

    Args:
        params: Query parameters:
            - start_date (str): Start date (YYYY-MM-DD)
            - end_date (str): End date (YYYY-MM-DD)
            - days (int): Days to look back if dates not specified

    Returns:
        Focus heatmap data or error message.
    """
    try:
        client = get_client(ctx)

        end_date = date.fromisoformat(params.end_date) if params.end_date else date.today()
        start_date = date.fromisoformat(params.start_date) if params.start_date else end_date - timedelta(days=params.days)

        data = await client.get_focus_heatmap(start_date, end_date)

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Focus Heatmap", "", f"Period: {start_date} to {end_date}", ""]
            total_duration = sum(d.get("duration", 0) for d in data)
            hours = total_duration / 3600
            lines.append(f"Total Focus Time: {hours:.1f} hours")
            return "\n".join(lines)
        else:
            return json.dumps({
                "start_date": str(start_date),
                "end_date": str(end_date),
                "data": data,
            }, indent=2)

    except Exception as e:
        return handle_error(e, "focus_heatmap")


@mcp.tool(
    name="ticktick_focus_by_tag",
    annotations={
        "title": "Get Focus Time by Tag",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_focus_by_tag(params: FocusStatsInput, ctx: Context) -> str:
    """
    Get focus time distribution by tag.

    Shows how focus time is distributed across different tags.

    Args:
        params: Query parameters:
            - start_date (str): Start date (YYYY-MM-DD)
            - end_date (str): End date (YYYY-MM-DD)
            - days (int): Days to look back if dates not specified

    Returns:
        Focus distribution by tag or error message.
    """
    try:
        client = get_client(ctx)

        end_date = date.fromisoformat(params.end_date) if params.end_date else date.today()
        start_date = date.fromisoformat(params.start_date) if params.start_date else end_date - timedelta(days=params.days)

        data = await client.get_focus_by_tag(start_date, end_date)

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Focus Time by Tag", "", f"Period: {start_date} to {end_date}", ""]

            if not data:
                lines.append("No focus data for this period.")
            else:
                for tag, seconds in sorted(data.items(), key=lambda x: x[1], reverse=True):
                    hours = seconds / 3600
                    lines.append(f"- **{tag}**: {hours:.1f} hours")

            return "\n".join(lines)
        else:
            return json.dumps({
                "start_date": str(start_date),
                "end_date": str(end_date),
                "tag_durations": data,
            }, indent=2)

    except Exception as e:
        return handle_error(e, "focus_by_tag")


# =============================================================================
# Sync Tools
# =============================================================================


@mcp.tool(
    name="ticktick_sync",
    annotations={
        "title": "Full Sync",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_sync(ctx: Context, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """
    Perform a full sync to get all data.

    Retrieves complete account state including all projects, tasks, tags,
    and settings in a single request.

    Returns:
        Summary of synced data or error message.
    """
    try:
        client = get_client(ctx)
        state = await client.sync()

        projects = state.get("projectProfiles", [])
        tasks = state.get("syncTaskBean", {}).get("update", [])
        tags = state.get("tags", [])
        groups = state.get("projectGroups", [])

        if response_format == ResponseFormat.MARKDOWN:
            lines = [
                "# TickTick Sync Complete",
                "",
                f"- **Projects**: {len(projects)}",
                f"- **Active Tasks**: {len(tasks)}",
                f"- **Tags**: {len(tags)}",
                f"- **Folders**: {len(groups)}",
                f"- **Inbox ID**: `{state.get('inboxId', 'N/A')}`",
            ]
            return "\n".join(lines)
        else:
            return json.dumps({
                "project_count": len(projects),
                "task_count": len(tasks),
                "tag_count": len(tags),
                "folder_count": len(groups),
                "inbox_id": state.get("inboxId"),
            }, indent=2)

    except Exception as e:
        return handle_error(e, "sync")


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Main entry point for the TickTick MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()

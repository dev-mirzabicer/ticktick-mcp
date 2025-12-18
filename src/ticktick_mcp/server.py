#!/usr/bin/env python3
"""
TickTick MCP Server - Comprehensive Task Management Integration.

This MCP server provides a complete interface for interacting with TickTick,
combining both V1 (OAuth2) and V2 (Session) APIs for maximum functionality.
It enables AI assistants to manage tasks, projects, tags, and track productivity.

=== CAPABILITIES ===

Task Management:
    - Create tasks with titles, due dates, priorities, tags, reminders, and recurrence
    - Create subtasks (parent-child relationships)
    - Update, complete, delete, and move tasks between projects
    - List active, completed, and overdue tasks
    - Search tasks by title or content

Project Management:
    - Create, read, update, and delete projects
    - Organize projects into folders
    - Get project details with all tasks

Tag Management:
    - Create, rename, merge, and delete tags
    - Tags support hierarchical nesting
    - Apply tags to tasks for organization

User Information:
    - Get user profile and account status
    - Access productivity statistics (completion rates, scores, levels)
    - Track focus/pomodoro sessions

=== TICKTICK API BEHAVIORS ===

IMPORTANT: TickTick has several unique API behaviors that tools account for:

1. SOFT DELETE: Deleting tasks moves them to trash (deleted=1) rather than
   permanently removing them. Deleted tasks remain accessible via get_task.

2. RECURRENCE REQUIRES START_DATE: Creating recurring tasks without a start_date
   silently ignores the recurrence rule. Always provide start_date with recurrence.

3. PARENT-CHILD RELATIONSHIPS: Setting parent_id during task creation is ignored
   by the API. Use the make_subtask tool to establish parent-child relationships.

4. DATE CLEARING: To clear a task's due_date or start_date, you must also clear
   both dates together (TickTick restores due_date from start_date otherwise).

5. TAG ORDER: The API does not preserve tag order - tags may be returned in
   any order regardless of how they were provided.

6. INBOX: The inbox is a special project that cannot be deleted. Its ID is
   available via get_status (inbox_id field).

=== AUTHENTICATION ===

This server requires BOTH V1 and V2 authentication for full functionality:

V1 (OAuth2) - Required for get_project_with_data:
    TICKTICK_CLIENT_ID      - OAuth2 client ID from developer portal
    TICKTICK_CLIENT_SECRET  - OAuth2 client secret
    TICKTICK_ACCESS_TOKEN   - Access token from OAuth2 flow

V2 (Session) - Required for most operations:
    TICKTICK_USERNAME       - TickTick account email
    TICKTICK_PASSWORD       - TickTick account password

Optional:
    TICKTICK_REDIRECT_URI   - OAuth2 redirect URI (default: http://localhost:8080/callback)
    TICKTICK_TIMEOUT        - Request timeout in seconds (default: 30)
    TICKTICK_DEVICE_ID      - Device identifier (auto-generated if not set)

=== RESPONSE FORMATS ===

All tools support two response formats via the `response_format` parameter:

- "markdown" (default): Human-readable formatted text with headers, lists, and
  timestamps in readable format. Best for displaying results to users.

- "json": Machine-readable structured data with all available fields.
  Best for programmatic processing or when specific field values are needed.

=== ERROR HANDLING ===

Tools return clear, actionable error messages:
- Authentication errors: Check credentials configuration
- Not found errors: Verify resource ID exists
- Validation errors: Check input parameters
- Rate limit errors: Wait before retrying
- Server errors: Retry or contact support
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
    TaskUnparentInput,
    TaskListInput,
    CompletedTasksInput,
    AbandonedTasksInput,
    DeletedTasksInput,
    ProjectCreateInput,
    ProjectGetInput,
    ProjectDeleteInput,
    ProjectUpdateInput,
    FolderCreateInput,
    FolderDeleteInput,
    FolderRenameInput,
    TagCreateInput,
    TagDeleteInput,
    TagRenameInput,
    TagMergeInput,
    TagUpdateInput,
    FocusStatsInput,
    SearchInput,
    HabitListInput,
    HabitGetInput,
    HabitCreateInput,
    HabitUpdateInput,
    HabitDeleteInput,
    HabitCheckinInput,
    HabitArchiveInput,
    HabitCheckinsInput,
)
from ticktick_mcp.models import Habit, HabitSection
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
# Constants
# =============================================================================

# Maximum response size in characters to prevent overwhelming context
CHARACTER_LIMIT = 25000

# Default pagination limits
DEFAULT_TASK_LIMIT = 50
DEFAULT_PROJECT_LIMIT = 100
MAX_TASK_LIMIT = 200


# =============================================================================
# Truncation Helper
# =============================================================================


def truncate_response(
    result: str,
    items_count: int,
    truncated_count: int | None = None,
) -> str:
    """
    Truncate response if it exceeds CHARACTER_LIMIT.

    Args:
        result: The formatted response string
        items_count: Total number of items before truncation
        truncated_count: Number of items after truncation (if different)

    Returns:
        Truncated response with guidance message if needed
    """
    if len(result) <= CHARACTER_LIMIT:
        return result

    # Find a good truncation point (after a complete item)
    truncate_at = CHARACTER_LIMIT - 500  # Leave room for message
    truncate_point = result.rfind("\n\n", 0, truncate_at)
    if truncate_point == -1:
        truncate_point = result.rfind("\n", 0, truncate_at)
    if truncate_point == -1:
        truncate_point = truncate_at

    truncated = result[:truncate_point]

    # Add truncation message
    message = (
        f"\n\n---\n"
        f"⚠️ **Response truncated** (exceeded {CHARACTER_LIMIT:,} characters)\n\n"
        f"Showing partial results. To see more:\n"
        f"- Use filters (project_id, tag, priority) to narrow results\n"
        f"- Use the 'limit' parameter to reduce the number of items\n"
        f"- Request response_format='json' for more compact output"
    )

    return truncated + message


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
    """
    Handle exceptions and return user-friendly, actionable error messages.

    Error messages include:
    1. What went wrong
    2. Why it might have happened
    3. Specific steps to resolve the issue
    """
    logger.exception("Error in %s: %s", operation, e)

    error_type = type(e).__name__
    error_str = str(e)

    if "Authentication" in error_type:
        return error_message(
            "Authentication failed",
            "NEXT STEPS:\n"
            "1. Verify environment variables are set:\n"
            "   - TICKTICK_CLIENT_ID (OAuth2 client ID)\n"
            "   - TICKTICK_CLIENT_SECRET (OAuth2 client secret)\n"
            "   - TICKTICK_ACCESS_TOKEN (OAuth2 access token)\n"
            "   - TICKTICK_USERNAME (TickTick account email)\n"
            "   - TICKTICK_PASSWORD (TickTick account password)\n"
            "2. Check that credentials are not expired\n"
            "3. Re-run OAuth2 flow if access token is invalid"
        )
    elif "NotFound" in error_type:
        resource_hint = ""
        if "task" in error_str.lower():
            resource_hint = (
                "HINTS:\n"
                "- Task may have been permanently deleted (not just trashed)\n"
                "- Use ticktick_list_tasks to see available tasks\n"
                "- Check if the task ID is correct"
            )
        elif "project" in error_str.lower():
            resource_hint = (
                "HINTS:\n"
                "- Use ticktick_list_projects to see available projects\n"
                "- The inbox project ID can be obtained from ticktick_get_status"
            )
        elif "tag" in error_str.lower():
            resource_hint = (
                "HINTS:\n"
                "- Use ticktick_list_tags to see available tags\n"
                "- Tag names are case-insensitive"
            )
        elif "folder" in error_str.lower() or "group" in error_str.lower():
            resource_hint = (
                "HINTS:\n"
                "- Use ticktick_list_folders to see available folders"
            )
        return error_message(
            f"Resource not found: {error_str}",
            resource_hint or "Verify the ID is correct and the resource exists."
        )
    elif "Validation" in error_type:
        return error_message(
            f"Invalid input: {error_str}",
            "Check the parameter types and constraints in the tool documentation."
        )
    elif "Configuration" in error_type:
        if "recurrence" in error_str.lower() and "start_date" in error_str.lower():
            return error_message(
                f"Configuration error: {error_str}",
                "TICKTICK REQUIREMENT: Recurring tasks require a start_date.\n"
                "Add a start_date parameter when setting recurrence rules."
            )
        return error_message(
            f"Configuration error: {error_str}",
            "Check your environment variables and tool parameters."
        )
    elif "RateLimit" in error_type:
        return error_message(
            "Rate limit exceeded",
            "NEXT STEPS:\n"
            "1. Wait 30-60 seconds before retrying\n"
            "2. Reduce the frequency of API calls\n"
            "3. Batch operations where possible"
        )
    elif "Quota" in error_type:
        return error_message(
            "Account quota exceeded",
            "HINTS:\n"
            "- Free accounts have limited projects/tasks\n"
            "- Delete unused projects or upgrade to Pro"
        )
    elif "Forbidden" in error_type:
        return error_message(
            f"Access denied: {error_str}",
            "You don't have permission to access this resource.\n"
            "Check if you're the owner or have appropriate sharing permissions."
        )
    elif "Server" in error_type:
        return error_message(
            f"TickTick server error: {error_str}",
            "NEXT STEPS:\n"
            "1. Wait a moment and retry the operation\n"
            "2. Check if TickTick service is operational\n"
            "3. Try with different parameters if the issue persists"
        )
    else:
        return error_message(
            f"Unexpected error: {error_str}",
            f"Error type: {error_type}\n"
            "If this persists, check the server logs for more details."
        )


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

    Creates a task with the specified properties. Tasks can include titles,
    due dates, priorities, tags, reminders, and recurrence rules.

    IMPORTANT TICKTICK BEHAVIORS:
    - If no project_id is specified, the task is created in the inbox
    - RECURRENCE REQUIRES start_date: If you set a recurrence rule without
      start_date, the recurrence will be silently ignored by TickTick
    - To create a SUBTASK, use ticktick_make_subtask after creating the task.
      Setting parent_id here does NOT work (TickTick API ignores it on creation)
    - Tags are created automatically if they don't exist

    Args:
        params: Task creation parameters:
            - title (str, required): Task title
            - project_id (str, optional): Project to create in (defaults to inbox).
              Get inbox ID from ticktick_get_status or project IDs from ticktick_list_projects
            - content (str, optional): Task notes/description
            - priority (str, optional): 'none' (default), 'low', 'medium', 'high'
            - start_date (str, optional): Start date in ISO format (REQUIRED for recurrence)
            - due_date (str, optional): Due date in ISO format (e.g., "2025-01-20T17:00:00")
            - tags (list[str], optional): Tag names to apply. Tags are case-insensitive
            - reminders (list[str], optional): Reminder triggers in iCal format
              (e.g., "TRIGGER:-PT30M" for 30 minutes before)
            - recurrence (str, optional): RRULE format (e.g., "RRULE:FREQ=DAILY;INTERVAL=1")
            - response_format (str): 'markdown' (default) or 'json'

    Returns:
        On success: Formatted task details showing all created properties
        On error: Error message with hints for resolution

        JSON format returns:
        {
            "id": "task_id",
            "title": "Task title",
            "project_id": "project_id",
            "status": 0,
            "priority": 0,
            "due_date": "2025-01-20T17:00:00Z",
            "tags": ["tag1", "tag2"],
            ...
        }

    Examples:
        Simple task:
            title="Buy groceries"

        Task with due date:
            title="Submit report", due_date="2025-01-20T17:00:00", priority="high"

        Recurring task (MUST include start_date):
            title="Daily standup", start_date="2025-01-15T09:00:00",
            recurrence="RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR"

        Task with tags and reminder:
            title="Meeting", tags=["work", "important"],
            reminders=["TRIGGER:-PT15M"]

    When NOT to use:
        - To create subtasks: Create task first, then use ticktick_make_subtask
        - To update existing task: Use ticktick_update_task instead
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
        total_count = len(tasks)
        tasks = tasks[: params.limit]

        if params.response_format == ResponseFormat.MARKDOWN:
            result = format_tasks_markdown(tasks)
        else:
            result = json.dumps(format_tasks_json(tasks), indent=2)

        # Apply truncation if response is too large
        return truncate_response(result, total_count, len(tasks))

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
    name="ticktick_unparent_subtask",
    annotations={
        "title": "Unparent Subtask",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_unparent_subtask(params: TaskUnparentInput, ctx: Context) -> str:
    """
    Remove a task from its parent (make it a top-level task).

    Removes the parent-child relationship, turning the subtask back into
    a regular top-level task.

    Args:
        params: Unparent parameters:
            - task_id (str): Subtask to unparent (required)
            - project_id (str): Project containing the task (required)

    Returns:
        Success confirmation or error message.

    Raises:
        Error if the task is not a subtask (has no parent).
    """
    try:
        client = get_client(ctx)
        await client.unparent_subtask(params.task_id, params.project_id)
        return success_message(f"Task `{params.task_id}` is now a top-level task.")

    except Exception as e:
        return handle_error(e, "unparent_subtask")


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
    name="ticktick_abandoned_tasks",
    annotations={
        "title": "Get Abandoned Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_abandoned_tasks(params: AbandonedTasksInput, ctx: Context) -> str:
    """
    Get recently abandoned ("won't do") tasks.

    Retrieves tasks that were marked as abandoned/won't do within the
    specified time period. Useful for reviewing decisions and deprioritized work.

    Args:
        params: Query parameters:
            - days (int): Number of days to look back (default 7)
            - limit (int): Maximum results (default 50)

    Returns:
        Formatted list of abandoned tasks or error message.
    """
    try:
        client = get_client(ctx)
        tasks = await client.get_abandoned_tasks(days=params.days, limit=params.limit)

        title = f"Abandoned Tasks (Last {params.days} Days)"

        if params.response_format == ResponseFormat.MARKDOWN:
            return format_tasks_markdown(tasks, title)
        else:
            return json.dumps(format_tasks_json(tasks), indent=2)

    except Exception as e:
        return handle_error(e, "abandoned_tasks")


@mcp.tool(
    name="ticktick_deleted_tasks",
    annotations={
        "title": "Get Deleted Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_deleted_tasks(params: DeletedTasksInput, ctx: Context) -> str:
    """
    Get deleted tasks (in trash).

    Retrieves tasks that have been deleted but are still in the trash.
    Tasks in trash can potentially be restored.

    Args:
        params: Query parameters:
            - limit (int): Maximum results (default 50)

    Returns:
        Formatted list of deleted tasks or error message.
    """
    try:
        client = get_client(ctx)
        tasks = await client.get_deleted_tasks(limit=params.limit)

        title = "Deleted Tasks (Trash)"

        if params.response_format == ResponseFormat.MARKDOWN:
            return format_tasks_markdown(tasks, title)
        else:
            return json.dumps(format_tasks_json(tasks), indent=2)

    except Exception as e:
        return handle_error(e, "deleted_tasks")


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
    name="ticktick_update_project",
    annotations={
        "title": "Update Project",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_update_project(params: ProjectUpdateInput, ctx: Context) -> str:
    """
    Update a project's properties.

    Updates project name, color, or folder assignment.

    Args:
        params: Update parameters:
            - project_id (str): Project to update (required)
            - name (str): New project name
            - color (str): New hex color code (e.g., '#F18181')
            - folder_id (str): New folder ID (use 'NONE' to remove from folder)

    Returns:
        Formatted updated project or error message.
    """
    try:
        client = get_client(ctx)

        # Handle "NONE" to remove from folder
        folder_id = params.folder_id
        if folder_id and folder_id.upper() == "NONE":
            folder_id = ""  # Empty string removes from folder

        project = await client.update_project(
            project_id=params.project_id,
            name=params.name,
            color=params.color,
            folder_id=folder_id,
        )

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Project Updated\n\n{format_project_markdown(project)}"
        else:
            return json.dumps({"success": True, "project": format_project_json(project)}, indent=2)

    except Exception as e:
        return handle_error(e, "update_project")


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
    name="ticktick_rename_folder",
    annotations={
        "title": "Rename Folder",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_rename_folder(params: FolderRenameInput, ctx: Context) -> str:
    """
    Rename a folder.

    Args:
        params: Rename parameters:
            - folder_id (str): Folder to rename (required)
            - name (str): New folder name (required)

    Returns:
        Formatted updated folder or error message.
    """
    try:
        client = get_client(ctx)
        folder = await client.rename_folder(params.folder_id, params.name)

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Folder Renamed\n\n- **{folder.name}** (`{folder.id}`)"
        else:
            return json.dumps({"success": True, "folder": {"id": folder.id, "name": folder.name}}, indent=2)

    except Exception as e:
        return handle_error(e, "rename_folder")


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
    name="ticktick_update_tag",
    annotations={
        "title": "Update Tag",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_update_tag(params: TagUpdateInput, ctx: Context) -> str:
    """
    Update a tag's properties.

    Updates tag color or parent.

    Args:
        params: Update parameters:
            - name (str): Tag name to update (required)
            - color (str): New hex color code (e.g., '#F18181')
            - parent (str): New parent tag name (empty string to remove parent)

    Returns:
        Formatted updated tag or error message.
    """
    try:
        client = get_client(ctx)

        # Handle empty string as None to remove parent
        parent = params.parent
        if parent == "":
            parent = None

        tag = await client.update_tag(params.name, color=params.color, parent=parent)

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Tag Updated\n\n{format_tag_markdown(tag)}"
        else:
            return json.dumps({"success": True, "tag": format_tag_json(tag)}, indent=2)

    except Exception as e:
        return handle_error(e, "update_tag")


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


@mcp.tool(
    name="ticktick_get_preferences",
    annotations={
        "title": "Get User Preferences",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_get_preferences(ctx: Context) -> str:
    """
    Get user preferences and settings.

    Retrieves user-configurable settings including:
    - timeZone: User's timezone
    - weekStartDay: First day of week (0=Sunday, 1=Monday)
    - startOfDay: Hour when day starts
    - dateFormat: Date display format
    - timeFormat: Time display format (12h/24h)
    - defaultReminder: Default reminder setting
    - And other user preferences

    Returns:
        JSON object with all user preferences.
    """
    try:
        client = get_client(ctx)
        preferences = await client.get_preferences()
        return json.dumps(preferences, indent=2)

    except Exception as e:
        return handle_error(e, "get_preferences")


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
# Habit Tools
# =============================================================================


def format_habit_markdown(habit: Habit) -> str:
    """Format a habit for markdown display."""
    lines = [
        f"## {habit.name}",
        f"- **ID**: `{habit.id}`",
        f"- **Type**: {habit.habit_type}",
        f"- **Goal**: {habit.goal} {habit.unit}",
    ]

    if habit.is_numeric:
        lines.append(f"- **Step**: +{habit.step}")

    lines.append(f"- **Status**: {'Archived' if habit.is_archived else 'Active'}")
    lines.append(f"- **Total Check-ins**: {habit.total_checkins}")
    lines.append(f"- **Current Streak**: {habit.current_streak}")

    if habit.target_days > 0:
        lines.append(f"- **Target**: {habit.target_days} days")

    if habit.color:
        lines.append(f"- **Color**: {habit.color}")

    if habit.repeat_rule:
        lines.append(f"- **Repeat**: `{habit.repeat_rule}`")

    if habit.reminders:
        lines.append(f"- **Reminders**: {', '.join(habit.reminders)}")

    if habit.encouragement:
        lines.append(f"- **Encouragement**: {habit.encouragement}")

    return "\n".join(lines)


def format_habit_json(habit: Habit) -> dict[str, Any]:
    """Format a habit for JSON output."""
    return {
        "id": habit.id,
        "name": habit.name,
        "type": habit.habit_type,
        "goal": habit.goal,
        "step": habit.step,
        "unit": habit.unit,
        "status": "archived" if habit.is_archived else "active",
        "total_checkins": habit.total_checkins,
        "current_streak": habit.current_streak,
        "target_days": habit.target_days,
        "color": habit.color,
        "icon": habit.icon,
        "repeat_rule": habit.repeat_rule,
        "reminders": habit.reminders,
        "section_id": habit.section_id,
        "encouragement": habit.encouragement,
        "created_time": habit.created_time.isoformat() if habit.created_time else None,
        "modified_time": habit.modified_time.isoformat() if habit.modified_time else None,
    }


def format_habits_markdown(habits: list[Habit], title: str = "Habits") -> str:
    """Format multiple habits for markdown display."""
    if not habits:
        return f"# {title}\n\nNo habits found."

    lines = [f"# {title}", f"*{len(habits)} habits*", ""]

    for habit in habits:
        status = "📦" if habit.is_archived else "✅" if habit.current_streak > 0 else "⏳"
        lines.append(f"### {status} {habit.name}")
        lines.append(f"- **ID**: `{habit.id}`")
        lines.append(f"- **Type**: {habit.habit_type}")
        lines.append(f"- **Streak**: {habit.current_streak} | Total: {habit.total_checkins}")
        if habit.target_days > 0:
            lines.append(f"- **Target**: {habit.target_days} days")
        lines.append("")

    return "\n".join(lines)


def format_habits_json(habits: list[Habit]) -> list[dict[str, Any]]:
    """Format multiple habits for JSON output."""
    return [format_habit_json(h) for h in habits]


def format_section_markdown(section: HabitSection) -> str:
    """Format a habit section for markdown display."""
    return f"- **{section.display_name}** (`{section.id}`)"


def format_sections_json(sections: list[HabitSection]) -> list[dict[str, Any]]:
    """Format habit sections for JSON output."""
    return [
        {"id": s.id, "name": s.name, "display_name": s.display_name}
        for s in sections
    ]


@mcp.tool(
    name="ticktick_habits",
    annotations={
        "title": "List Habits",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_habits(params: HabitListInput, ctx: Context) -> str:
    """
    List all habits.

    Retrieves all habits including their status, streaks, and goals.

    Args:
        params: Query parameters:
            - include_archived (bool): Include archived habits (default: False)
            - response_format (str): Output format ("markdown" or "json")

    Returns:
        List of habits with their details.
    """
    try:
        client = get_client(ctx)
        habits = await client.get_all_habits()

        if not params.include_archived:
            habits = [h for h in habits if h.is_active]

        if params.response_format == ResponseFormat.MARKDOWN:
            return format_habits_markdown(habits)
        else:
            return json.dumps(format_habits_json(habits), indent=2)

    except Exception as e:
        return handle_error(e, "list_habits")


@mcp.tool(
    name="ticktick_habit",
    annotations={
        "title": "Get Habit",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_habit(params: HabitGetInput, ctx: Context) -> str:
    """
    Get a specific habit by ID.

    Args:
        params: Query parameters:
            - habit_id (str): Habit ID (required)
            - response_format (str): Output format

    Returns:
        Habit details.
    """
    try:
        client = get_client(ctx)
        habit = await client.get_habit(params.habit_id)

        if params.response_format == ResponseFormat.MARKDOWN:
            return format_habit_markdown(habit)
        else:
            return json.dumps(format_habit_json(habit), indent=2)

    except Exception as e:
        return handle_error(e, "get_habit")


@mcp.tool(
    name="ticktick_habit_sections",
    annotations={
        "title": "List Habit Sections",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_habit_sections(ctx: Context, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """
    List habit sections (time-of-day groupings).

    Sections organize habits by time of day: Morning, Afternoon, Night.

    Returns:
        List of habit sections with their IDs.
    """
    try:
        client = get_client(ctx)
        sections = await client.get_habit_sections()

        if response_format == ResponseFormat.MARKDOWN:
            lines = ["# Habit Sections", ""]
            for section in sections:
                lines.append(format_section_markdown(section))
            return "\n".join(lines)
        else:
            return json.dumps(format_sections_json(sections), indent=2)

    except Exception as e:
        return handle_error(e, "habit_sections")


@mcp.tool(
    name="ticktick_create_habit",
    annotations={
        "title": "Create Habit",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def ticktick_create_habit(params: HabitCreateInput, ctx: Context) -> str:
    """
    Create a new habit.

    Creates a habit with the specified configuration. Habits can be boolean
    (yes/no) or numeric (count/measure).

    Args:
        params: Habit parameters:
            - name (str): Habit name (required)
            - habit_type (str): "Boolean" or "Real" (default: Boolean)
            - goal (float): Target value (default: 1.0)
            - step (float): Increment for numeric (default: 1.0)
            - unit (str): Unit of measurement (default: Count)
            - color (str): Hex color (optional)
            - section_id (str): Time-of-day section (optional)
            - repeat_rule (str): RRULE pattern (default: daily)
            - reminders (list[str]): Times in HH:MM format
            - target_days (int): Goal in days (0 = no target)
            - encouragement (str): Motivational message

    Returns:
        Created habit details.
    """
    try:
        client = get_client(ctx)
        habit = await client.create_habit(
            name=params.name,
            habit_type=params.habit_type,
            goal=params.goal,
            step=params.step,
            unit=params.unit,
            color=params.color or "#97E38B",
            section_id=params.section_id,
            repeat_rule=params.repeat_rule,
            reminders=params.reminders,
            target_days=params.target_days,
            encouragement=params.encouragement,
        )

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Habit Created\n\n{format_habit_markdown(habit)}"
        else:
            return json.dumps({"success": True, "habit": format_habit_json(habit)}, indent=2)

    except Exception as e:
        return handle_error(e, "create_habit")


@mcp.tool(
    name="ticktick_update_habit",
    annotations={
        "title": "Update Habit",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_update_habit(params: HabitUpdateInput, ctx: Context) -> str:
    """
    Update a habit's properties.

    Args:
        params: Update parameters:
            - habit_id (str): Habit ID (required)
            - name (str): New name
            - goal (float): New goal
            - step (float): New step
            - unit (str): New unit
            - color (str): New hex color
            - section_id (str): New section ID
            - repeat_rule (str): New RRULE pattern
            - reminders (list[str]): New reminders
            - target_days (int): New target days
            - encouragement (str): New message

    Returns:
        Updated habit details.
    """
    try:
        client = get_client(ctx)
        habit = await client.update_habit(
            habit_id=params.habit_id,
            name=params.name,
            goal=params.goal,
            step=params.step,
            unit=params.unit,
            color=params.color,
            section_id=params.section_id,
            repeat_rule=params.repeat_rule,
            reminders=params.reminders,
            target_days=params.target_days,
            encouragement=params.encouragement,
        )

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Habit Updated\n\n{format_habit_markdown(habit)}"
        else:
            return json.dumps({"success": True, "habit": format_habit_json(habit)}, indent=2)

    except Exception as e:
        return handle_error(e, "update_habit")


@mcp.tool(
    name="ticktick_delete_habit",
    annotations={
        "title": "Delete Habit",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_delete_habit(params: HabitDeleteInput, ctx: Context) -> str:
    """
    Delete a habit.

    Permanently removes the habit and all its check-in history.

    Args:
        params: Delete parameters:
            - habit_id (str): Habit ID to delete (required)

    Returns:
        Confirmation message.
    """
    try:
        client = get_client(ctx)
        await client.delete_habit(params.habit_id)
        return success_message(f"Habit `{params.habit_id}` deleted successfully.")

    except Exception as e:
        return handle_error(e, "delete_habit")


@mcp.tool(
    name="ticktick_checkin_habit",
    annotations={
        "title": "Check In Habit",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def ticktick_checkin_habit(params: HabitCheckinInput, ctx: Context) -> str:
    """
    Check in a habit (complete for today).

    Records a check-in for the habit, incrementing the total and streak.

    Args:
        params: Check-in parameters:
            - habit_id (str): Habit ID (required)
            - value (float): Check-in value (default: 1.0)

    Returns:
        Updated habit with new totals.
    """
    try:
        client = get_client(ctx)
        habit = await client.checkin_habit(params.habit_id, params.value)

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [
                f"# Habit Checked In!",
                "",
                f"**{habit.name}** completed!",
                f"- **Total Check-ins**: {habit.total_checkins}",
                f"- **Current Streak**: {habit.current_streak}",
            ]
            return "\n".join(lines)
        else:
            return json.dumps({
                "success": True,
                "habit": format_habit_json(habit),
            }, indent=2)

    except Exception as e:
        return handle_error(e, "checkin_habit")


@mcp.tool(
    name="ticktick_archive_habit",
    annotations={
        "title": "Archive Habit",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_archive_habit(params: HabitArchiveInput, ctx: Context) -> str:
    """
    Archive a habit.

    Archived habits are hidden but preserved. Use unarchive to restore.

    Args:
        params: Archive parameters:
            - habit_id (str): Habit ID to archive (required)

    Returns:
        Updated habit.
    """
    try:
        client = get_client(ctx)
        habit = await client.archive_habit(params.habit_id)

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Habit Archived\n\n**{habit.name}** has been archived."
        else:
            return json.dumps({"success": True, "habit": format_habit_json(habit)}, indent=2)

    except Exception as e:
        return handle_error(e, "archive_habit")


@mcp.tool(
    name="ticktick_unarchive_habit",
    annotations={
        "title": "Unarchive Habit",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_unarchive_habit(params: HabitArchiveInput, ctx: Context) -> str:
    """
    Unarchive a habit.

    Restores an archived habit to active status.

    Args:
        params: Unarchive parameters:
            - habit_id (str): Habit ID to unarchive (required)

    Returns:
        Updated habit.
    """
    try:
        client = get_client(ctx)
        habit = await client.unarchive_habit(params.habit_id)

        if params.response_format == ResponseFormat.MARKDOWN:
            return f"# Habit Unarchived\n\n**{habit.name}** has been restored."
        else:
            return json.dumps({"success": True, "habit": format_habit_json(habit)}, indent=2)

    except Exception as e:
        return handle_error(e, "unarchive_habit")


@mcp.tool(
    name="ticktick_habit_checkins",
    annotations={
        "title": "Get Habit Check-in History",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ticktick_habit_checkins(params: HabitCheckinsInput, ctx: Context) -> str:
    """
    Get habit check-in history.

    Retrieves check-in records for the specified habits.

    Args:
        params: Query parameters:
            - habit_ids (list[str]): List of habit IDs to query (required)
            - after_stamp (int): Date stamp (YYYYMMDD) to get check-ins after

    Returns:
        Check-in history for each habit.
    """
    try:
        client = get_client(ctx)
        data = await client.get_habit_checkins(
            habit_ids=params.habit_ids,
            after_stamp=params.after_stamp,
        )

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Habit Check-in History", ""]
            for habit_id, checkins in data.items():
                lines.append(f"## Habit `{habit_id}`")
                if not checkins:
                    lines.append("No check-ins found.")
                else:
                    for checkin in checkins:
                        lines.append(f"- {checkin.checkin_stamp}: {checkin.value}")
                lines.append("")
            return "\n".join(lines)
        else:
            # Convert HabitCheckin objects to dicts
            result = {}
            for habit_id, checkins in data.items():
                result[habit_id] = [
                    {
                        "checkin_stamp": c.checkin_stamp,
                        "value": c.value,
                        "goal": c.goal,
                        "status": c.status,
                    }
                    for c in checkins
                ]
            return json.dumps(result, indent=2)

    except Exception as e:
        return handle_error(e, "habit_checkins")


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

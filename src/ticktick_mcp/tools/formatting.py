"""
Response Formatting Utilities for TickTick MCP Tools.

This module provides consistent formatting for tool responses
in both Markdown and JSON formats.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ticktick_mcp.models import Task, Project, ProjectGroup, Tag, User, UserStatus, UserStatistics
from ticktick_mcp.tools.inputs import ResponseFormat

# Maximum response size in characters
CHARACTER_LIMIT = 25000


def format_datetime(dt: datetime | None) -> str:
    """Format a datetime for human-readable display."""
    if dt is None:
        return "Not set"
    return dt.strftime("%Y-%m-%d %H:%M %Z").strip()


def format_date(dt: datetime | None) -> str:
    """Format a date for human-readable display."""
    if dt is None:
        return "Not set"
    return dt.strftime("%Y-%m-%d")


def priority_label(priority: int) -> str:
    """Convert priority int to label."""
    labels = {0: "None", 1: "Low", 3: "Medium", 5: "High"}
    return labels.get(priority, "None")


def priority_emoji(priority: int) -> str:
    """Get emoji for priority level."""
    emojis = {0: "", 1: "", 3: "", 5: ""}
    return emojis.get(priority, "")


def status_label(status: int) -> str:
    """Convert status int to label."""
    labels = {-1: "Abandoned", 0: "Active", 1: "Completed", 2: "Completed"}
    return labels.get(status, "Unknown")


# =============================================================================
# Task Formatting
# =============================================================================


def format_task_markdown(task: Task) -> str:
    """Format a single task as Markdown."""
    lines = []

    # Title with priority indicator
    priority_indicator = priority_emoji(task.priority)
    title = task.title or "(No title)"
    lines.append(f"## {priority_indicator} {title}")
    lines.append("")

    # Key details
    lines.append(f"- **ID**: `{task.id}`")
    lines.append(f"- **Project**: `{task.project_id}`")
    lines.append(f"- **Status**: {status_label(task.status)}")
    lines.append(f"- **Priority**: {priority_label(task.priority)}")

    if task.due_date:
        lines.append(f"- **Due**: {format_datetime(task.due_date)}")
    if task.start_date:
        lines.append(f"- **Start**: {format_datetime(task.start_date)}")

    if task.tags:
        tags_str = ", ".join(f"`{t}`" for t in task.tags)
        lines.append(f"- **Tags**: {tags_str}")

    if task.content:
        lines.append("")
        lines.append("### Notes")
        lines.append(task.content)

    if task.items:
        lines.append("")
        lines.append("### Subtasks")
        for item in task.items:
            checkbox = "[x]" if item.is_completed else "[ ]"
            lines.append(f"- {checkbox} {item.title or '(No title)'}")

    return "\n".join(lines)


def format_task_json(task: Task) -> dict[str, Any]:
    """Format a single task as JSON-serializable dict."""
    return {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "content": task.content,
        "status": task.status,
        "status_label": status_label(task.status),
        "priority": task.priority,
        "priority_label": priority_label(task.priority),
        "start_date": task.start_date.isoformat() if task.start_date else None,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "completed_time": task.completed_time.isoformat() if task.completed_time else None,
        "tags": task.tags,
        "is_all_day": task.is_all_day,
        "time_zone": task.time_zone,
        "repeat_flag": task.repeat_flag,
        "parent_id": task.parent_id,
        "child_ids": task.child_ids,
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "status": item.status,
                "completed": item.is_completed,
            }
            for item in task.items
        ],
    }


def format_tasks_markdown(tasks: list[Task], title: str = "Tasks") -> str:
    """Format multiple tasks as Markdown."""
    if not tasks:
        return f"# {title}\n\nNo tasks found."

    lines = [f"# {title}", "", f"Found {len(tasks)} task(s):", ""]

    for task in tasks:
        priority_indicator = priority_emoji(task.priority)
        task_title = task.title or "(No title)"
        due_str = f" | Due: {format_date(task.due_date)}" if task.due_date else ""
        tags_str = f" | Tags: {', '.join(task.tags)}" if task.tags else ""

        lines.append(f"- {priority_indicator} **{task_title}** (`{task.id}`){due_str}{tags_str}")

    return "\n".join(lines)


def format_tasks_json(tasks: list[Task]) -> dict[str, Any]:
    """Format multiple tasks as JSON."""
    return {
        "count": len(tasks),
        "tasks": [format_task_json(t) for t in tasks],
    }


# =============================================================================
# Project Formatting
# =============================================================================


def format_project_markdown(project: Project) -> str:
    """Format a single project as Markdown."""
    lines = []

    lines.append(f"## {project.name}")
    lines.append("")
    lines.append(f"- **ID**: `{project.id}`")
    lines.append(f"- **Kind**: {project.kind or 'TASK'}")
    lines.append(f"- **View Mode**: {project.view_mode or 'list'}")

    if project.color:
        lines.append(f"- **Color**: {project.color}")
    if project.group_id:
        lines.append(f"- **Folder**: `{project.group_id}`")
    if project.closed:
        lines.append("- **Status**: Archived")

    return "\n".join(lines)


def format_project_json(project: Project) -> dict[str, Any]:
    """Format a single project as JSON."""
    return {
        "id": project.id,
        "name": project.name,
        "color": project.color,
        "kind": project.kind,
        "view_mode": project.view_mode,
        "group_id": project.group_id,
        "closed": project.closed,
        "sort_order": project.sort_order,
    }


def format_projects_markdown(projects: list[Project], title: str = "Projects") -> str:
    """Format multiple projects as Markdown."""
    if not projects:
        return f"# {title}\n\nNo projects found."

    lines = [f"# {title}", "", f"Found {len(projects)} project(s):", ""]

    for project in projects:
        color_indicator = f"({project.color})" if project.color else ""
        lines.append(f"- **{project.name}** (`{project.id}`) {color_indicator}")

    return "\n".join(lines)


def format_projects_json(projects: list[Project]) -> dict[str, Any]:
    """Format multiple projects as JSON."""
    return {
        "count": len(projects),
        "projects": [format_project_json(p) for p in projects],
    }


# =============================================================================
# Tag Formatting
# =============================================================================


def format_tag_markdown(tag: Tag) -> str:
    """Format a single tag as Markdown."""
    lines = []

    lines.append(f"## {tag.label}")
    lines.append("")
    lines.append(f"- **Name**: `{tag.name}`")

    if tag.color:
        lines.append(f"- **Color**: {tag.color}")
    if tag.parent:
        lines.append(f"- **Parent**: `{tag.parent}`")

    return "\n".join(lines)


def format_tag_json(tag: Tag) -> dict[str, Any]:
    """Format a single tag as JSON."""
    return {
        "name": tag.name,
        "label": tag.label,
        "color": tag.color,
        "parent": tag.parent,
        "sort_order": tag.sort_order,
    }


def format_tags_markdown(tags: list[Tag], title: str = "Tags") -> str:
    """Format multiple tags as Markdown."""
    if not tags:
        return f"# {title}\n\nNo tags found."

    lines = [f"# {title}", "", f"Found {len(tags)} tag(s):", ""]

    for tag in tags:
        color_indicator = f"({tag.color})" if tag.color else ""
        parent_indicator = f" (in {tag.parent})" if tag.parent else ""
        lines.append(f"- **{tag.label}** (`{tag.name}`) {color_indicator}{parent_indicator}")

    return "\n".join(lines)


def format_tags_json(tags: list[Tag]) -> dict[str, Any]:
    """Format multiple tags as JSON."""
    return {
        "count": len(tags),
        "tags": [format_tag_json(t) for t in tags],
    }


# =============================================================================
# Folder Formatting
# =============================================================================


def format_folder_markdown(folder: ProjectGroup) -> str:
    """Format a single folder as Markdown."""
    return f"- **{folder.name}** (`{folder.id}`)"


def format_folder_json(folder: ProjectGroup) -> dict[str, Any]:
    """Format a single folder as JSON."""
    return {
        "id": folder.id,
        "name": folder.name,
        "sort_order": folder.sort_order,
    }


def format_folders_markdown(folders: list[ProjectGroup], title: str = "Folders") -> str:
    """Format multiple folders as Markdown."""
    if not folders:
        return f"# {title}\n\nNo folders found."

    lines = [f"# {title}", "", f"Found {len(folders)} folder(s):", ""]

    for folder in folders:
        lines.append(format_folder_markdown(folder))

    return "\n".join(lines)


def format_folders_json(folders: list[ProjectGroup]) -> dict[str, Any]:
    """Format multiple folders as JSON."""
    return {
        "count": len(folders),
        "folders": [format_folder_json(f) for f in folders],
    }


# =============================================================================
# User Formatting
# =============================================================================


def format_user_markdown(user: User) -> str:
    """Format user profile as Markdown."""
    lines = ["# User Profile", ""]

    lines.append(f"- **Username**: {user.username}")
    if user.display_name:
        lines.append(f"- **Display Name**: {user.display_name}")
    if user.name:
        lines.append(f"- **Name**: {user.name}")
    if user.email:
        lines.append(f"- **Email**: {user.email}")
    if user.locale:
        lines.append(f"- **Locale**: {user.locale}")
    lines.append(f"- **Verified Email**: {'Yes' if user.verified_email else 'No'}")

    return "\n".join(lines)


def format_user_status_markdown(status: UserStatus) -> str:
    """Format user status as Markdown."""
    lines = ["# Account Status", ""]

    lines.append(f"- **Username**: {status.username}")
    lines.append(f"- **User ID**: {status.user_id}")
    lines.append(f"- **Inbox ID**: {status.inbox_id}")
    lines.append(f"- **Pro Account**: {'Yes' if status.is_pro else 'No'}")

    if status.is_pro and status.pro_end_date:
        lines.append(f"- **Pro Expires**: {status.pro_end_date}")

    lines.append(f"- **Team User**: {'Yes' if status.team_user else 'No'}")

    return "\n".join(lines)


def format_statistics_markdown(stats: UserStatistics) -> str:
    """Format user statistics as Markdown."""
    lines = ["# Productivity Statistics", ""]

    lines.append(f"- **Level**: {stats.level}")
    lines.append(f"- **Score**: {stats.score}")
    lines.append("")

    lines.append("## Task Completion")
    lines.append(f"- Today: {stats.today_completed}")
    lines.append(f"- Yesterday: {stats.yesterday_completed}")
    lines.append(f"- All Time: {stats.total_completed}")
    lines.append("")

    if stats.total_pomo_count > 0:
        lines.append("## Focus/Pomodoro")
        lines.append(f"- Today: {stats.today_pomo_count} pomos ({stats.today_pomo_duration_minutes:.1f} min)")
        lines.append(f"- Yesterday: {stats.yesterday_pomo_count} pomos")
        lines.append(f"- All Time: {stats.total_pomo_count} pomos ({stats.total_pomo_duration_hours:.1f} hours)")

    return "\n".join(lines)


# =============================================================================
# Response Helpers
# =============================================================================


def format_response(
    data: Any,
    response_format: ResponseFormat,
    markdown_formatter: callable,
    json_formatter: callable,
) -> str:
    """
    Format a response based on the requested format.

    Args:
        data: The data to format
        response_format: Desired output format
        markdown_formatter: Function to format as Markdown
        json_formatter: Function to format as JSON dict

    Returns:
        Formatted string response
    """
    if response_format == ResponseFormat.MARKDOWN:
        result = markdown_formatter(data)
    else:
        result = json.dumps(json_formatter(data), indent=2, default=str)

    # Check character limit
    if len(result) > CHARACTER_LIMIT:
        if response_format == ResponseFormat.MARKDOWN:
            return (
                f"{result[:CHARACTER_LIMIT]}\n\n"
                f"---\n"
                f"*Response truncated. Use filters to narrow results.*"
            )
        else:
            return json.dumps({
                "truncated": True,
                "message": "Response truncated due to size. Use filters to narrow results.",
                "partial_data": result[:CHARACTER_LIMIT],
            })

    return result


def success_message(message: str) -> str:
    """Format a success message."""
    return f"**Success**: {message}"


def error_message(error: str, suggestion: str | None = None) -> str:
    """Format an error message with optional suggestion."""
    msg = f"**Error**: {error}"
    if suggestion:
        msg += f"\n\n*Suggestion*: {suggestion}"
    return msg

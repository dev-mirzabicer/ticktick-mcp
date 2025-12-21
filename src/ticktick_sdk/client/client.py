"""
High-Level TickTick Client.

This module provides the main TickTickClient class, which is the
primary entry point for interacting with TickTick.

The client wraps the UnifiedTickTickAPI and provides a clean,
user-friendly interface with additional convenience methods.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from types import TracebackType
from typing import Any, TypeVar

from ticktick_sdk.models import (
    Task,
    Project,
    ProjectGroup,
    ProjectData,
    Tag,
    User,
    UserStatus,
    UserStatistics,
    Habit,
    HabitSection,
    HabitCheckin,
    HabitPreferences,
)
from ticktick_sdk.settings import TickTickSettings, get_settings
from ticktick_sdk.unified import UnifiedTickTickAPI

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="TickTickClient")


class TickTickClient:
    """
    High-level TickTick client.

    This is the main entry point for interacting with TickTick.
    It provides a clean, user-friendly interface with convenience methods.

    The client requires BOTH V1 (OAuth2) and V2 (session) authentication
    to provide full functionality.

    Usage:
        # From settings (environment variables)
        async with TickTickClient.from_settings() as client:
            tasks = await client.get_all_tasks()

        # With explicit credentials
        async with TickTickClient(
            client_id="...",
            client_secret="...",
            v1_access_token="...",
            username="...",
            password="...",
        ) as client:
            tasks = await client.get_all_tasks()
    """

    def __init__(
        self,
        # V1 OAuth2 credentials
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8080/callback",
        v1_access_token: str | None = None,
        # V2 Session credentials
        username: str | None = None,
        password: str | None = None,
        # General
        timeout: float = 30.0,
        device_id: str | None = None,
    ) -> None:
        self._api = UnifiedTickTickAPI(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            v1_access_token=v1_access_token,
            username=username,
            password=password,
            timeout=timeout,
            device_id=device_id,
        )
        self._initialized = False

    @classmethod
    def from_settings(cls, settings: TickTickSettings | None = None) -> TickTickClient:
        """
        Create a client from settings.

        Args:
            settings: TickTickSettings instance (defaults to global settings)

        Returns:
            TickTickClient instance
        """
        if settings is None:
            settings = get_settings()

        # Validate settings
        settings.validate_all_ready()

        return cls(
            client_id=settings.client_id,
            client_secret=settings.client_secret.get_secret_value(),
            redirect_uri=settings.redirect_uri,
            v1_access_token=settings.get_v1_access_token(),
            username=settings.username,
            password=settings.get_v2_password(),
            timeout=settings.timeout,
            device_id=settings.device_id,
        )

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def connect(self) -> None:
        """
        Connect to TickTick and authenticate.

        This initializes both V1 and V2 API connections.
        """
        await self._api.initialize()
        self._initialized = True
        logger.info("TickTick client connected")

    async def disconnect(self) -> None:
        """Disconnect from TickTick."""
        await self._api.close()
        self._initialized = False
        logger.info("TickTick client disconnected")

    async def __aenter__(self: T) -> T:
        """Enter async context manager."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._initialized

    @property
    def inbox_id(self) -> str | None:
        """Get the inbox project ID."""
        return self._api.inbox_id

    # =========================================================================
    # Sync
    # =========================================================================

    async def sync(self) -> dict[str, Any]:
        """
        Get complete account state.

        Returns all projects, tasks, tags, and settings.

        Returns:
            Complete sync state
        """
        return await self._api.sync_all()

    # =========================================================================
    # Tasks
    # =========================================================================

    async def get_all_tasks(self) -> list[Task]:
        """
        Get all active tasks.

        Returns:
            List of all active tasks
        """
        return await self._api.list_all_tasks()

    async def get_task(self, task_id: str, project_id: str | None = None) -> Task:
        """
        Get a task by ID.

        Args:
            task_id: Task ID
            project_id: Project ID (optional, needed for V1 fallback)

        Returns:
            Task object
        """
        return await self._api.get_task(task_id, project_id)

    async def create_task(
        self,
        title: str,
        project_id: str | None = None,
        *,
        content: str | None = None,
        description: str | None = None,
        priority: int | str | None = None,
        start_date: datetime | None = None,
        due_date: datetime | None = None,
        time_zone: str | None = None,
        all_day: bool | None = None,
        reminders: list[str] | None = None,
        recurrence: str | None = None,
        tags: list[str] | None = None,
        parent_id: str | None = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            title: Task title
            project_id: Project ID (defaults to inbox)
            content: Task content/notes
            description: Checklist description
            priority: Priority (0/none, 1/low, 3/medium, 5/high)
            start_date: Start date
            due_date: Due date
            time_zone: Timezone
            all_day: All-day task
            reminders: List of reminder triggers (e.g., "TRIGGER:-PT30M")
            recurrence: Recurrence rule (RRULE format)
            tags: List of tag names
            parent_id: Parent task ID (for subtasks)

        Returns:
            Created task
        """
        # Convert string priority to int
        if isinstance(priority, str):
            priority_map = {"none": 0, "low": 1, "medium": 3, "high": 5}
            priority = priority_map.get(priority.lower(), 0)

        return await self._api.create_task(
            title=title,
            project_id=project_id,
            content=content,
            desc=description,
            priority=priority,
            start_date=start_date,
            due_date=due_date,
            time_zone=time_zone,
            is_all_day=all_day,
            reminders=reminders,
            repeat_flag=recurrence,
            tags=tags,
            parent_id=parent_id,
        )

    async def update_task(self, task: Task) -> Task:
        """
        Update a task.

        Args:
            task: Task with updated fields

        Returns:
            Updated task
        """
        return await self._api.update_task(task)

    async def complete_task(self, task_id: str, project_id: str) -> None:
        """
        Mark a task as complete.

        Args:
            task_id: Task ID
            project_id: Project ID
        """
        await self._api.complete_task(task_id, project_id)

    async def delete_task(self, task_id: str, project_id: str) -> None:
        """
        Delete a task.

        Args:
            task_id: Task ID
            project_id: Project ID
        """
        await self._api.delete_task(task_id, project_id)

    async def get_completed_tasks(
        self,
        days: int = 7,
        limit: int = 100,
    ) -> list[Task]:
        """
        Get recently completed tasks.

        Args:
            days: Number of days to look back
            limit: Maximum number of tasks

        Returns:
            List of completed tasks
        """
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        return await self._api.list_completed_tasks(from_date, to_date, limit)

    async def move_task(
        self,
        task_id: str,
        from_project_id: str,
        to_project_id: str,
    ) -> None:
        """
        Move a task to a different project.

        Args:
            task_id: Task ID
            from_project_id: Current project ID
            to_project_id: Target project ID
        """
        await self._api.move_task(task_id, from_project_id, to_project_id)

    async def make_subtask(
        self,
        task_id: str,
        parent_id: str,
        project_id: str,
    ) -> None:
        """
        Make a task a subtask of another task.

        Args:
            task_id: Task to make a subtask
            parent_id: Parent task ID
            project_id: Project ID
        """
        await self._api.set_task_parent(task_id, project_id, parent_id)

    async def unparent_subtask(
        self,
        task_id: str,
        project_id: str,
    ) -> None:
        """
        Remove a subtask from its parent (make it a top-level task).

        Args:
            task_id: Subtask to unparent
            project_id: Project ID

        Raises:
            TickTickNotFoundError: If the task does not exist
            TickTickAPIError: If the task is not a subtask
        """
        await self._api.unset_task_parent(task_id, project_id)

    async def get_abandoned_tasks(
        self,
        days: int = 7,
        limit: int = 100,
    ) -> list[Task]:
        """
        Get recently abandoned ("won't do") tasks.

        Args:
            days: Number of days to look back
            limit: Maximum number of tasks

        Returns:
            List of abandoned tasks
        """
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        return await self._api.list_abandoned_tasks(from_date, to_date, limit)

    async def get_deleted_tasks(
        self,
        limit: int = 100,
    ) -> list[Task]:
        """
        Get deleted tasks (in trash).

        Args:
            limit: Maximum number of tasks

        Returns:
            List of deleted tasks
        """
        return await self._api.list_deleted_tasks(0, limit)

    # =========================================================================
    # Projects
    # =========================================================================

    async def get_all_projects(self) -> list[Project]:
        """
        Get all projects.

        Returns:
            List of projects
        """
        return await self._api.list_projects()

    async def get_project(self, project_id: str) -> Project:
        """
        Get a project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project object
        """
        return await self._api.get_project(project_id)

    async def get_project_tasks(self, project_id: str) -> ProjectData:
        """
        Get a project with its tasks and columns.

        Args:
            project_id: Project ID

        Returns:
            ProjectData with project, tasks, and columns
        """
        return await self._api.get_project_with_data(project_id)

    async def create_project(
        self,
        name: str,
        *,
        color: str | None = None,
        kind: str = "TASK",
        view_mode: str = "list",
        folder_id: str | None = None,
    ) -> Project:
        """
        Create a new project.

        Args:
            name: Project name
            color: Hex color (e.g., "#F18181")
            kind: Project type ("TASK" or "NOTE")
            view_mode: View mode ("list", "kanban", "timeline")
            folder_id: Parent folder ID

        Returns:
            Created project
        """
        return await self._api.create_project(
            name=name,
            color=color,
            kind=kind,
            view_mode=view_mode,
            group_id=folder_id,
        )

    async def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        color: str | None = None,
        folder_id: str | None = None,
    ) -> Project:
        """
        Update a project's properties.

        Args:
            project_id: Project ID
            name: New name
            color: New hex color (e.g., "#F18181")
            folder_id: New folder ID (use "NONE" to remove from folder)

        Returns:
            Updated project
        """
        return await self._api.update_project(
            project_id=project_id,
            name=name,
            color=color,
            folder_id=folder_id,
        )

    async def delete_project(self, project_id: str) -> None:
        """
        Delete a project.

        Args:
            project_id: Project ID
        """
        await self._api.delete_project(project_id)

    # =========================================================================
    # Folders (Project Groups)
    # =========================================================================

    async def get_all_folders(self) -> list[ProjectGroup]:
        """
        Get all folders/project groups.

        Returns:
            List of folders
        """
        return await self._api.list_project_groups()

    async def create_folder(self, name: str) -> ProjectGroup:
        """
        Create a folder.

        Args:
            name: Folder name

        Returns:
            Created folder
        """
        return await self._api.create_project_group(name)

    async def rename_folder(self, folder_id: str, name: str) -> ProjectGroup:
        """
        Rename a folder.

        Args:
            folder_id: Folder ID
            name: New name

        Returns:
            Updated folder
        """
        return await self._api.update_project_group(folder_id, name)

    async def delete_folder(self, folder_id: str) -> None:
        """
        Delete a folder.

        Args:
            folder_id: Folder ID
        """
        await self._api.delete_project_group(folder_id)

    # =========================================================================
    # Tags
    # =========================================================================

    async def get_all_tags(self) -> list[Tag]:
        """
        Get all tags.

        Returns:
            List of tags
        """
        return await self._api.list_tags()

    async def create_tag(
        self,
        name: str,
        *,
        color: str | None = None,
        parent: str | None = None,
    ) -> Tag:
        """
        Create a tag.

        Args:
            name: Tag name
            color: Hex color
            parent: Parent tag name (for nesting)

        Returns:
            Created tag
        """
        return await self._api.create_tag(name, color=color, parent=parent)

    async def update_tag(
        self,
        name: str,
        *,
        color: str | None = None,
        parent: str | None = None,
    ) -> Tag:
        """
        Update a tag's properties.

        Args:
            name: Tag name (lowercase identifier)
            color: New hex color
            parent: New parent tag name (or None to remove parent)

        Returns:
            Updated tag
        """
        return await self._api.update_tag(name, color=color, parent=parent)

    async def delete_tag(self, name: str) -> None:
        """
        Delete a tag.

        Args:
            name: Tag name
        """
        await self._api.delete_tag(name)

    async def rename_tag(self, old_name: str, new_name: str) -> None:
        """
        Rename a tag.

        Args:
            old_name: Current name
            new_name: New name
        """
        await self._api.rename_tag(old_name, new_name)

    async def merge_tags(self, source: str, target: str) -> None:
        """
        Merge one tag into another.

        Args:
            source: Tag to merge (will be deleted)
            target: Tag to keep
        """
        await self._api.merge_tags(source, target)

    # =========================================================================
    # User
    # =========================================================================

    async def get_profile(self) -> User:
        """
        Get user profile.

        Returns:
            User profile
        """
        return await self._api.get_user_profile()

    async def get_status(self) -> UserStatus:
        """
        Get user status (subscription info).

        Returns:
            User status
        """
        return await self._api.get_user_status()

    async def get_statistics(self) -> UserStatistics:
        """
        Get productivity statistics.

        Returns:
            User statistics
        """
        return await self._api.get_user_statistics()

    async def get_preferences(self) -> dict[str, Any]:
        """
        Get user preferences and settings.

        Returns:
            User preferences dictionary containing settings like:
            - timeZone: User's timezone
            - weekStartDay: First day of week (0=Sunday, 1=Monday, etc.)
            - startOfDay: Hour when day starts
            - dateFormat: Date display format
            - timeFormat: Time display format (12h/24h)
            - defaultReminder: Default reminder setting
            - And many more user-configurable options
        """
        return await self._api.get_user_preferences()

    # =========================================================================
    # Focus/Pomodoro
    # =========================================================================

    async def get_focus_heatmap(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Get focus/pomodoro heatmap.

        Args:
            start_date: Start date (defaults to `days` ago)
            end_date: End date (defaults to today)
            days: Number of days if dates not specified

        Returns:
            Heatmap data
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        return await self._api.get_focus_heatmap(start_date, end_date)

    async def get_focus_by_tag(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int = 30,
    ) -> dict[str, int]:
        """
        Get focus time by tag.

        Args:
            start_date: Start date (defaults to `days` ago)
            end_date: End date (defaults to today)
            days: Number of days if dates not specified

        Returns:
            Dict of tag -> duration in seconds
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        return await self._api.get_focus_by_tag(start_date, end_date)

    # =========================================================================
    # Habits
    # =========================================================================

    async def get_all_habits(self) -> list[Habit]:
        """
        Get all habits.

        Returns:
            List of habits
        """
        return await self._api.list_habits()

    async def get_habit(self, habit_id: str) -> Habit:
        """
        Get a habit by ID.

        Args:
            habit_id: Habit ID

        Returns:
            Habit object

        Raises:
            TickTickNotFoundError: If habit not found
        """
        return await self._api.get_habit(habit_id)

    async def get_habit_sections(self) -> list[HabitSection]:
        """
        Get habit sections (time-of-day groupings).

        Returns:
            List of habit sections (_morning, _afternoon, _night)
        """
        return await self._api.list_habit_sections()

    async def get_habit_preferences(self) -> HabitPreferences:
        """
        Get habit preferences/settings.

        Returns:
            Habit preferences (showInCalendar, showInToday, enabled, etc.)
        """
        return await self._api.get_habit_preferences()

    async def create_habit(
        self,
        name: str,
        *,
        habit_type: str = "Boolean",
        goal: float = 1.0,
        step: float = 0.0,
        unit: str = "Count",
        icon: str = "habit_daily_check_in",
        color: str = "#97E38B",
        section_id: str | None = None,
        repeat_rule: str = "RRULE:FREQ=WEEKLY;BYDAY=SU,MO,TU,WE,TH,FR,SA",
        reminders: list[str] | None = None,
        target_days: int = 0,
        encouragement: str = "",
    ) -> Habit:
        """
        Create a new habit.

        Args:
            name: Habit name
            habit_type: "Boolean" for yes/no, "Real" for numeric
            goal: Target goal value (1.0 for boolean)
            step: Increment step for numeric habits
            unit: Unit of measurement
            icon: Icon resource name
            color: Hex color
            section_id: Time-of-day section ID
            repeat_rule: RRULE recurrence pattern
            reminders: List of reminder times ("HH:MM")
            target_days: Goal in days (0 = no target)
            encouragement: Motivational message

        Returns:
            Created habit
        """
        return await self._api.create_habit(
            name=name,
            habit_type=habit_type,
            goal=goal,
            step=step,
            unit=unit,
            icon=icon,
            color=color,
            section_id=section_id,
            repeat_rule=repeat_rule,
            reminders=reminders,
            target_days=target_days,
            encouragement=encouragement,
        )

    async def update_habit(
        self,
        habit_id: str,
        *,
        name: str | None = None,
        goal: float | None = None,
        step: float | None = None,
        unit: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        section_id: str | None = None,
        repeat_rule: str | None = None,
        reminders: list[str] | None = None,
        target_days: int | None = None,
        encouragement: str | None = None,
    ) -> Habit:
        """
        Update a habit.

        Args:
            habit_id: Habit ID
            name: New name
            goal: New goal
            step: New step
            unit: New unit
            icon: New icon
            color: New color
            section_id: New section ID
            repeat_rule: New repeat rule
            reminders: New reminders
            target_days: New target days
            encouragement: New encouragement

        Returns:
            Updated habit

        Raises:
            TickTickNotFoundError: If habit not found
        """
        return await self._api.update_habit(
            habit_id=habit_id,
            name=name,
            goal=goal,
            step=step,
            unit=unit,
            icon=icon,
            color=color,
            section_id=section_id,
            repeat_rule=repeat_rule,
            reminders=reminders,
            target_days=target_days,
            encouragement=encouragement,
        )

    async def delete_habit(self, habit_id: str) -> None:
        """
        Delete a habit.

        Args:
            habit_id: Habit ID

        Raises:
            TickTickNotFoundError: If habit not found
        """
        await self._api.delete_habit(habit_id)

    async def checkin_habit(
        self,
        habit_id: str,
        value: float = 1.0,
        checkin_date: date | None = None,
    ) -> Habit:
        """
        Check in a habit for a specific date.

        If checkin_date is None or today, increments both totalCheckIns and
        currentStreak. If checkin_date is a past date (backdating), only
        increments totalCheckIns and creates a check-in record for that date.

        Args:
            habit_id: Habit ID
            value: Check-in value (1.0 for boolean habits)
            checkin_date: Date to check in for. None means today.
                          Use a past date to backdate the check-in.

        Returns:
            Updated habit

        Raises:
            TickTickNotFoundError: If habit not found

        Example:
            # Check in for today
            await client.checkin_habit("habit_id")

            # Backdate a check-in to December 15, 2025
            from datetime import date
            await client.checkin_habit("habit_id", checkin_date=date(2025, 12, 15))
        """
        return await self._api.checkin_habit(habit_id, value, checkin_date)

    async def archive_habit(self, habit_id: str) -> Habit:
        """
        Archive a habit.

        Args:
            habit_id: Habit ID

        Returns:
            Updated habit

        Raises:
            TickTickNotFoundError: If habit not found
        """
        return await self._api.archive_habit(habit_id)

    async def unarchive_habit(self, habit_id: str) -> Habit:
        """
        Unarchive a habit.

        Args:
            habit_id: Habit ID

        Returns:
            Updated habit

        Raises:
            TickTickNotFoundError: If habit not found
        """
        return await self._api.unarchive_habit(habit_id)

    async def get_habit_checkins(
        self,
        habit_ids: list[str],
        after_stamp: int = 0,
    ) -> dict[str, list[HabitCheckin]]:
        """
        Get habit check-in data.

        Args:
            habit_ids: List of habit IDs to query
            after_stamp: Date stamp (YYYYMMDD) to get check-ins after (0 for all)

        Returns:
            Dict mapping habit IDs to lists of check-in records
        """
        return await self._api.get_habit_checkins(habit_ids, after_stamp)

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def quick_add(self, text: str, project_id: str | None = None) -> Task:
        """
        Quick add a task with just a title.

        Args:
            text: Task title
            project_id: Project ID (defaults to inbox)

        Returns:
            Created task
        """
        return await self.create_task(text, project_id)

    async def get_today_tasks(self) -> list[Task]:
        """
        Get tasks due today.

        Returns:
            List of tasks due today
        """
        today = date.today()
        all_tasks = await self.get_all_tasks()
        return [
            task for task in all_tasks
            if task.due_date and task.due_date.date() == today
        ]

    async def get_overdue_tasks(self) -> list[Task]:
        """
        Get overdue tasks.

        Returns:
            List of overdue tasks
        """
        today = date.today()
        all_tasks = await self.get_all_tasks()
        return [
            task for task in all_tasks
            if task.due_date
            and task.due_date.date() < today
            and not task.is_completed
        ]

    async def get_tasks_by_tag(self, tag_name: str) -> list[Task]:
        """
        Get tasks with a specific tag.

        Args:
            tag_name: Tag name

        Returns:
            List of tasks with the tag
        """
        all_tasks = await self.get_all_tasks()
        tag_lower = tag_name.lower()
        return [
            task for task in all_tasks
            if any(t.lower() == tag_lower for t in task.tags)
        ]

    async def get_tasks_by_priority(self, priority: int | str) -> list[Task]:
        """
        Get tasks with a specific priority.

        Args:
            priority: Priority level (0/none, 1/low, 3/medium, 5/high or string)

        Returns:
            List of tasks with the priority
        """
        if isinstance(priority, str):
            priority_map = {"none": 0, "low": 1, "medium": 3, "high": 5}
            priority = priority_map.get(priority.lower(), 0)

        all_tasks = await self.get_all_tasks()
        return [task for task in all_tasks if task.priority == priority]

    async def search_tasks(self, query: str) -> list[Task]:
        """
        Search tasks by title or content.

        Args:
            query: Search query

        Returns:
            Matching tasks
        """
        query_lower = query.lower()
        all_tasks = await self.get_all_tasks()
        return [
            task for task in all_tasks
            if (task.title and query_lower in task.title.lower())
            or (task.content and query_lower in task.content.lower())
        ]

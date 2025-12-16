"""
Unified TickTick API.

This module provides the UnifiedTickTickAPI class, which is the main
entry point for version-agnostic TickTick operations.

It manages both V1 and V2 clients, routes operations appropriately,
and converts between unified models and API-specific formats.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from types import TracebackType
from typing import Any, TypeVar

from ticktick_mcp.api.v1 import TickTickV1Client
from ticktick_mcp.api.v2 import TickTickV2Client
from ticktick_mcp.constants import TaskStatus
from ticktick_mcp.exceptions import (
    TickTickAPIError,
    TickTickAPIUnavailableError,
    TickTickAuthenticationError,
    TickTickConfigurationError,
)
from ticktick_mcp.models import (
    Task,
    Project,
    ProjectGroup,
    ProjectData,
    Tag,
    User,
    UserStatus,
    UserStatistics,
)
from ticktick_mcp.unified.router import APIRouter

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="UnifiedTickTickAPI")


class UnifiedTickTickAPI:
    """
    Unified TickTick API providing version-agnostic operations.

    This class manages both V1 and V2 API clients and provides
    a single interface for all TickTick operations. It automatically
    routes operations to the appropriate API version.

    Both V1 and V2 authentication are REQUIRED for full functionality.

    Usage:
        async with UnifiedTickTickAPI(
            # V1 OAuth2
            client_id="...",
            client_secret="...",
            v1_access_token="...",
            # V2 Session
            username="...",
            password="...",
        ) as api:
            # Full functionality available
            tasks = await api.list_all_tasks()
            projects = await api.list_projects()
            tags = await api.list_tags()
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
        # Store credentials for lazy initialization
        self._v1_credentials = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "access_token": v1_access_token,
            "timeout": timeout,
        }
        self._v2_credentials = {
            "username": username,
            "password": password,
            "device_id": device_id,
            "timeout": timeout,
        }

        # Clients (lazy initialized)
        self._v1_client: TickTickV1Client | None = None
        self._v2_client: TickTickV2Client | None = None

        # Router
        self._router: APIRouter | None = None

        # State
        self._initialized = False
        self._inbox_id: str | None = None

    # =========================================================================
    # Initialization & Lifecycle
    # =========================================================================

    async def initialize(self) -> None:
        """
        Initialize both API clients.

        This must be called before using the API, or use the async context manager.
        """
        if self._initialized:
            return

        errors: list[str] = []

        # Initialize V1 client
        try:
            self._v1_client = TickTickV1Client(
                client_id=self._v1_credentials["client_id"],
                client_secret=self._v1_credentials["client_secret"],
                redirect_uri=self._v1_credentials["redirect_uri"],
                access_token=self._v1_credentials["access_token"],
                timeout=self._v1_credentials["timeout"],
            )
            logger.info("V1 client initialized")
        except Exception as e:
            errors.append(f"V1 initialization failed: {e}")
            logger.error("Failed to initialize V1 client: %s", e)

        # Initialize V2 client
        try:
            self._v2_client = TickTickV2Client(
                device_id=self._v2_credentials["device_id"],
                timeout=self._v2_credentials["timeout"],
            )

            # Authenticate V2 if credentials provided
            if self._v2_credentials["username"] and self._v2_credentials["password"]:
                session = await self._v2_client.authenticate(
                    self._v2_credentials["username"],
                    self._v2_credentials["password"],
                )
                self._inbox_id = session.inbox_id
                logger.info("V2 client authenticated")
            else:
                errors.append("V2 credentials not provided")
        except Exception as e:
            errors.append(f"V2 initialization failed: {e}")
            logger.error("Failed to initialize V2 client: %s", e)

        # Create router
        self._router = APIRouter(
            v1_client=self._v1_client,
            v2_client=self._v2_client,
        )

        # Verify clients
        verification = await self._router.verify_clients()
        if not verification.get("v1"):
            errors.append("V1 authentication verification failed")
        if not verification.get("v2"):
            errors.append("V2 authentication verification failed")

        # Check if we have both APIs
        if not self._router.is_fully_configured:
            raise TickTickConfigurationError(
                "Both V1 and V2 APIs are required. " + "; ".join(errors),
            )

        self._initialized = True
        logger.info("Unified API initialized successfully")

    async def close(self) -> None:
        """Close all API clients."""
        if self._v1_client:
            await self._v1_client.close()
        if self._v2_client:
            await self._v2_client.close()
        self._initialized = False

    async def __aenter__(self: T) -> T:
        """Enter async context manager."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.close()

    def _ensure_initialized(self) -> None:
        """Ensure the API is initialized."""
        if not self._initialized:
            raise TickTickConfigurationError(
                "API not initialized. Use 'await api.initialize()' or async context manager."
            )

    @property
    def inbox_id(self) -> str | None:
        """Get the user's inbox ID."""
        return self._inbox_id

    @property
    def router(self) -> APIRouter:
        """Get the API router."""
        self._ensure_initialized()
        return self._router  # type: ignore

    # =========================================================================
    # Sync
    # =========================================================================

    async def sync_all(self) -> dict[str, Any]:
        """
        Sync all data from TickTick.

        Returns complete state including projects, tasks, tags, etc.
        This is a V2-only operation.

        Returns:
            Complete sync state dictionary
        """
        self._ensure_initialized()
        return await self._v2_client.sync()  # type: ignore

    # =========================================================================
    # Task Operations
    # =========================================================================

    async def list_all_tasks(self) -> list[Task]:
        """
        List all active tasks.

        Returns:
            List of all active tasks
        """
        self._ensure_initialized()
        state = await self._v2_client.sync()  # type: ignore
        tasks_data = state.get("syncTaskBean", {}).get("update", [])
        return [Task.from_v2(t) for t in tasks_data]

    async def get_task(self, task_id: str, project_id: str | None = None) -> Task:
        """
        Get a single task by ID.

        Args:
            task_id: Task identifier
            project_id: Project ID (required for V1 fallback)

        Returns:
            Task object
        """
        self._ensure_initialized()

        # Try V2 first (doesn't need project_id)
        if self._router.has_v2:
            try:
                data = await self._v2_client.get_task(task_id)  # type: ignore
                return Task.from_v2(data)
            except TickTickAPIError:
                pass

        # Fallback to V1
        if self._router.has_v1 and project_id:
            data = await self._v1_client.get_task(project_id, task_id)  # type: ignore
            return Task.from_v1(data)

        raise TickTickAPIUnavailableError(
            "Could not get task",
            operation="get_task",
        )

    async def create_task(
        self,
        title: str,
        project_id: str | None = None,
        *,
        content: str | None = None,
        desc: str | None = None,
        priority: int | None = None,
        start_date: datetime | None = None,
        due_date: datetime | None = None,
        time_zone: str | None = None,
        is_all_day: bool | None = None,
        reminders: list[str] | None = None,
        repeat_flag: str | None = None,
        tags: list[str] | None = None,
        parent_id: str | None = None,
    ) -> Task:
        """
        Create a new task.

        Uses V2 API primarily for richer features (tags, parent_id).

        Args:
            title: Task title
            project_id: Project ID (defaults to inbox)
            content: Task content
            desc: Checklist description
            priority: Priority (0, 1, 3, 5)
            start_date: Start date
            due_date: Due date
            time_zone: Timezone
            is_all_day: All-day flag
            reminders: List of reminder triggers
            repeat_flag: Recurrence rule
            tags: List of tags (V2 only)
            parent_id: Parent task ID for subtasks (V2 only)

        Returns:
            Created task
        """
        self._ensure_initialized()

        # Default to inbox if no project specified
        if project_id is None:
            project_id = self._inbox_id
        if project_id is None:
            raise TickTickConfigurationError("No project ID provided and inbox ID unknown")

        # Format dates
        start_str = Task.format_datetime(start_date, "v2") if start_date else None
        due_str = Task.format_datetime(due_date, "v2") if due_date else None

        # Use V2 (primary) for richer features
        if self._router.has_v2:
            response = await self._v2_client.create_task(  # type: ignore
                title=title,
                project_id=project_id,
                content=content,
                desc=desc,
                priority=priority,
                start_date=start_str,
                due_date=due_str,
                time_zone=time_zone,
                is_all_day=is_all_day,
                reminders=[{"trigger": r} for r in reminders] if reminders else None,
                repeat_flag=repeat_flag,
                tags=tags,
                parent_id=parent_id,
            )

            # Get the created task ID from response
            task_id = next(iter(response.get("id2etag", {}).keys()), None)
            if task_id:
                return await self.get_task(task_id, project_id)

        # Fallback to V1 (loses tags and parent_id)
        if self._router.has_v1:
            data = await self._v1_client.create_task(  # type: ignore
                title=title,
                project_id=project_id,
                content=content,
                desc=desc,
                priority=priority,
                start_date=start_str,
                due_date=due_str,
                time_zone=time_zone,
                is_all_day=is_all_day,
                reminders=reminders,
                repeat_flag=repeat_flag,
            )
            return Task.from_v1(data)

        raise TickTickAPIUnavailableError(
            "Could not create task",
            operation="create_task",
        )

    async def update_task(
        self,
        task: Task,
    ) -> Task:
        """
        Update a task.

        Args:
            task: Task object with updated fields

        Returns:
            Updated task
        """
        self._ensure_initialized()

        # Use V2 (primary)
        if self._router.has_v2:
            data = task.to_v2_dict()
            response = await self._v2_client.batch_tasks(update=[data])  # type: ignore

            # Return updated task
            return await self.get_task(task.id, task.project_id)

        # Fallback to V1
        if self._router.has_v1:
            data = await self._v1_client.update_task(  # type: ignore
                task_id=task.id,
                project_id=task.project_id,
                title=task.title,
                content=task.content,
                desc=task.desc,
                is_all_day=task.is_all_day,
                start_date=task.format_datetime(task.start_date, "v1"),
                due_date=task.format_datetime(task.due_date, "v1"),
                time_zone=task.time_zone,
                reminders=[r.trigger for r in task.reminders] if task.reminders else None,
                repeat_flag=task.repeat_flag,
                priority=task.priority,
                sort_order=task.sort_order,
            )
            return Task.from_v1(data)

        raise TickTickAPIUnavailableError(
            "Could not update task",
            operation="update_task",
        )

    async def complete_task(self, task_id: str, project_id: str) -> None:
        """
        Mark a task as complete.

        Uses V1 API primarily (dedicated endpoint).

        Args:
            task_id: Task ID
            project_id: Project ID
        """
        self._ensure_initialized()

        # Use V1 (primary) - has dedicated endpoint
        if self._router.has_v1:
            await self._v1_client.complete_task(project_id, task_id)  # type: ignore
            return

        # Fallback to V2 - update status
        if self._router.has_v2:
            await self._v2_client.update_task(  # type: ignore
                task_id=task_id,
                project_id=project_id,
                status=TaskStatus.COMPLETED,
                completed_time=Task.format_datetime(datetime.now(), "v2"),
            )
            return

        raise TickTickAPIUnavailableError(
            "Could not complete task",
            operation="complete_task",
        )

    async def delete_task(self, task_id: str, project_id: str) -> None:
        """
        Delete a task.

        Args:
            task_id: Task ID
            project_id: Project ID
        """
        self._ensure_initialized()

        # Use V2 (primary)
        if self._router.has_v2:
            await self._v2_client.delete_task(project_id, task_id)  # type: ignore
            return

        # Fallback to V1
        if self._router.has_v1:
            await self._v1_client.delete_task(project_id, task_id)  # type: ignore
            return

        raise TickTickAPIUnavailableError(
            "Could not delete task",
            operation="delete_task",
        )

    async def list_completed_tasks(
        self,
        from_date: datetime,
        to_date: datetime,
        limit: int = 100,
    ) -> list[Task]:
        """
        List completed tasks in a date range.

        V2-only operation.

        Args:
            from_date: Start date
            to_date: End date
            limit: Maximum results

        Returns:
            List of completed tasks
        """
        self._ensure_initialized()
        data = await self._v2_client.get_completed_tasks(from_date, to_date, limit)  # type: ignore
        return [Task.from_v2(t) for t in data]

    async def move_task(
        self,
        task_id: str,
        from_project_id: str,
        to_project_id: str,
    ) -> None:
        """
        Move a task to a different project.

        V2-only operation.

        Args:
            task_id: Task ID
            from_project_id: Source project ID
            to_project_id: Destination project ID
        """
        self._ensure_initialized()
        await self._v2_client.move_task(task_id, from_project_id, to_project_id)  # type: ignore

    async def set_task_parent(
        self,
        task_id: str,
        project_id: str,
        parent_id: str,
    ) -> None:
        """
        Make a task a subtask of another task.

        V2-only operation.

        Args:
            task_id: Task to make a subtask
            project_id: Project ID
            parent_id: Parent task ID
        """
        self._ensure_initialized()
        await self._v2_client.set_task_parent(task_id, project_id, parent_id)  # type: ignore

    # =========================================================================
    # Project Operations
    # =========================================================================

    async def list_projects(self) -> list[Project]:
        """
        List all projects.

        Returns:
            List of projects
        """
        self._ensure_initialized()

        # Use V2 (primary) for more metadata
        if self._router.has_v2:
            state = await self._v2_client.sync()  # type: ignore
            projects_data = state.get("projectProfiles", [])
            return [Project.from_v2(p) for p in projects_data]

        # Fallback to V1
        if self._router.has_v1:
            data = await self._v1_client.get_projects()  # type: ignore
            return [Project.from_v1(p) for p in data]

        raise TickTickAPIUnavailableError(
            "Could not list projects",
            operation="list_projects",
        )

    async def get_project(self, project_id: str) -> Project:
        """
        Get a project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project object
        """
        self._ensure_initialized()

        # Use V1 (primary) - has dedicated endpoint
        if self._router.has_v1:
            data = await self._v1_client.get_project(project_id)  # type: ignore
            return Project.from_v1(data)

        # Fallback to V2 - get from sync
        if self._router.has_v2:
            state = await self._v2_client.sync()  # type: ignore
            for p in state.get("projectProfiles", []):
                if p.get("id") == project_id:
                    return Project.from_v2(p)

        raise TickTickAPIUnavailableError(
            "Could not get project",
            operation="get_project",
        )

    async def get_project_with_data(self, project_id: str) -> ProjectData:
        """
        Get a project with its tasks and columns.

        V1-only operation.

        Args:
            project_id: Project ID

        Returns:
            ProjectData with project, tasks, and columns
        """
        self._ensure_initialized()

        if not self._router.has_v1:
            raise TickTickAPIUnavailableError(
                "V1 API required for get_project_with_data",
                operation="get_project_with_data",
            )

        data = await self._v1_client.get_project_with_data(project_id)  # type: ignore
        return ProjectData.from_v1(data)

    async def create_project(
        self,
        name: str,
        *,
        color: str | None = None,
        kind: str | None = None,
        view_mode: str | None = None,
        group_id: str | None = None,
    ) -> Project:
        """
        Create a new project.

        Args:
            name: Project name
            color: Hex color
            kind: Project kind (TASK, NOTE)
            view_mode: View mode (list, kanban, timeline)
            group_id: Parent folder ID

        Returns:
            Created project
        """
        self._ensure_initialized()

        # Use V2 (primary)
        if self._router.has_v2:
            response = await self._v2_client.create_project(  # type: ignore
                name=name,
                color=color,
                kind=kind,
                view_mode=view_mode,
                group_id=group_id,
            )
            project_id = next(iter(response.get("id2etag", {}).keys()), None)
            if project_id:
                return await self.get_project(project_id)

        # Fallback to V1
        if self._router.has_v1:
            data = await self._v1_client.create_project(  # type: ignore
                name=name,
                color=color,
                view_mode=view_mode,
                kind=kind,
            )
            return Project.from_v1(data)

        raise TickTickAPIUnavailableError(
            "Could not create project",
            operation="create_project",
        )

    async def delete_project(self, project_id: str) -> None:
        """
        Delete a project.

        Args:
            project_id: Project ID
        """
        self._ensure_initialized()

        # Use V2 (primary)
        if self._router.has_v2:
            await self._v2_client.delete_project(project_id)  # type: ignore
            return

        # Fallback to V1
        if self._router.has_v1:
            await self._v1_client.delete_project(project_id)  # type: ignore
            return

        raise TickTickAPIUnavailableError(
            "Could not delete project",
            operation="delete_project",
        )

    # =========================================================================
    # Project Group Operations (V2 Only)
    # =========================================================================

    async def list_project_groups(self) -> list[ProjectGroup]:
        """
        List all project groups/folders.

        V2-only operation.

        Returns:
            List of project groups
        """
        self._ensure_initialized()
        state = await self._v2_client.sync()  # type: ignore
        groups_data = state.get("projectGroups", [])
        return [ProjectGroup.from_v2(g) for g in groups_data]

    async def create_project_group(self, name: str) -> ProjectGroup:
        """
        Create a project group/folder.

        V2-only operation.

        Args:
            name: Group name

        Returns:
            Created group
        """
        self._ensure_initialized()
        response = await self._v2_client.create_project_group(name)  # type: ignore
        group_id = next(iter(response.get("id2etag", {}).keys()), None)

        # Get from sync to return full object
        groups = await self.list_project_groups()
        for group in groups:
            if group.id == group_id:
                return group

        # Return minimal if not found
        return ProjectGroup(id=group_id or "", name=name)

    async def delete_project_group(self, group_id: str) -> None:
        """
        Delete a project group/folder.

        V2-only operation.

        Args:
            group_id: Group ID
        """
        self._ensure_initialized()
        await self._v2_client.delete_project_group(group_id)  # type: ignore

    # =========================================================================
    # Tag Operations (V2 Only)
    # =========================================================================

    async def list_tags(self) -> list[Tag]:
        """
        List all tags.

        V2-only operation.

        Returns:
            List of tags
        """
        self._ensure_initialized()
        state = await self._v2_client.sync()  # type: ignore
        tags_data = state.get("tags", [])
        return [Tag.from_v2(t) for t in tags_data]

    async def create_tag(
        self,
        label: str,
        *,
        color: str | None = None,
        parent: str | None = None,
    ) -> Tag:
        """
        Create a tag.

        V2-only operation.

        Args:
            label: Tag display name
            color: Hex color
            parent: Parent tag name

        Returns:
            Created tag
        """
        self._ensure_initialized()
        await self._v2_client.create_tag(  # type: ignore
            label=label,
            color=color,
            parent=parent,
        )
        return Tag.create(label, color, parent)

    async def delete_tag(self, name: str) -> None:
        """
        Delete a tag.

        V2-only operation.

        Args:
            name: Tag name (lowercase identifier)
        """
        self._ensure_initialized()
        await self._v2_client.delete_tag(name)  # type: ignore

    async def rename_tag(self, old_name: str, new_label: str) -> None:
        """
        Rename a tag.

        V2-only operation.

        Args:
            old_name: Current tag name
            new_label: New tag label
        """
        self._ensure_initialized()
        await self._v2_client.rename_tag(old_name, new_label)  # type: ignore

    async def merge_tags(self, source_name: str, target_name: str) -> None:
        """
        Merge one tag into another.

        V2-only operation.

        Args:
            source_name: Tag to merge from (will be deleted)
            target_name: Tag to merge into
        """
        self._ensure_initialized()
        await self._v2_client.merge_tags(source_name, target_name)  # type: ignore

    # =========================================================================
    # User Operations (V2 Only)
    # =========================================================================

    async def get_user_profile(self) -> User:
        """
        Get user profile.

        V2-only operation.

        Returns:
            User profile
        """
        self._ensure_initialized()
        data = await self._v2_client.get_user_profile()  # type: ignore
        return User.from_v2(data)

    async def get_user_status(self) -> UserStatus:
        """
        Get user subscription status.

        V2-only operation.

        Returns:
            User status
        """
        self._ensure_initialized()
        data = await self._v2_client.get_user_status()  # type: ignore
        return UserStatus.from_v2(data)

    async def get_user_statistics(self) -> UserStatistics:
        """
        Get user productivity statistics.

        V2-only operation.

        Returns:
            User statistics
        """
        self._ensure_initialized()
        data = await self._v2_client.get_user_statistics()  # type: ignore
        return UserStatistics.from_v2(data)

    # =========================================================================
    # Focus/Pomodoro Operations (V2 Only)
    # =========================================================================

    async def get_focus_heatmap(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """
        Get focus/pomodoro heatmap.

        V2-only operation.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Heatmap data
        """
        self._ensure_initialized()
        return await self._v2_client.get_focus_heatmap(start_date, end_date)  # type: ignore

    async def get_focus_by_tag(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        """
        Get focus time by tag.

        V2-only operation.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Dict of tag -> duration in seconds
        """
        self._ensure_initialized()
        data = await self._v2_client.get_focus_by_tag(start_date, end_date)  # type: ignore
        return data.get("tagDurations", {})

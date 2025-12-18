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

from ticktick_sdk.api.v1 import TickTickV1Client
from ticktick_sdk.api.v2 import TickTickV2Client
from ticktick_sdk.constants import TaskStatus
from ticktick_sdk.exceptions import (
    TickTickAPIError,
    TickTickAPIUnavailableError,
    TickTickAuthenticationError,
    TickTickConfigurationError,
    TickTickForbiddenError,
    TickTickNotFoundError,
    TickTickQuotaExceededError,
)
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
from ticktick_sdk.unified.router import APIRouter

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="UnifiedTickTickAPI")


# Error codes that map to NotFoundError in batch responses
_BATCH_NOT_FOUND_ERRORS = frozenset({
    "TASK_NOT_FOUND",
    "PROJECT_NOT_FOUND",
    "TAG_NOT_FOUND",
    "task not exists",
    "project not found",
})

# Error codes that map to QuotaExceededError
_BATCH_QUOTA_ERRORS = frozenset({
    "EXCEED_QUOTA",
})


def _check_batch_response_errors(
    response: dict[str, Any],
    operation: str,
    resource_ids: list[str] | None = None,
) -> None:
    """Check a V2 batch response for errors and raise appropriate exceptions.

    V2 batch endpoints return HTTP 200 with errors in the `id2error` field.
    This function checks for those errors and raises semantic exceptions.

    Args:
        response: The batch response dict with 'id2etag' and 'id2error' fields
        operation: Operation name for error messages
        resource_ids: Optional list of resource IDs to check for errors

    Raises:
        TickTickNotFoundError: If a resource was not found
        TickTickQuotaExceededError: If quota was exceeded
        TickTickAPIError: For other errors
    """
    id2error = response.get("id2error", {})
    if not id2error:
        return

    # If specific IDs provided, only check those
    if resource_ids:
        errors_to_check = {k: v for k, v in id2error.items() if k in resource_ids}
    else:
        errors_to_check = id2error

    if not errors_to_check:
        return

    # Check each error and raise the appropriate exception
    for resource_id, error_msg in errors_to_check.items():
        error_upper = error_msg.upper() if error_msg else ""

        # Check for not found errors
        if any(nf in error_upper or nf.upper() in error_upper for nf in _BATCH_NOT_FOUND_ERRORS):
            raise TickTickNotFoundError(
                f"Resource not found: {error_msg}",
                resource_id=resource_id,
            )

        # Check for quota errors
        if any(qe in error_upper for qe in _BATCH_QUOTA_ERRORS):
            raise TickTickQuotaExceededError(
                f"Quota exceeded: {error_msg}",
            )

        # Generic error for anything else
        raise TickTickAPIError(
            f"{operation} failed: {error_msg}",
            details={"resource_id": resource_id, "error": error_msg},
        )


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
            project_id: Project ID (required for V1 if V2 unavailable)

        Returns:
            Task object

        Raises:
            TickTickNotFoundError: If the task does not exist
            TickTickForbiddenError: If access to the task is forbidden
            TickTickAPIUnavailableError: If no API is available for this operation
        """
        self._ensure_initialized()

        # Use V2 (primary) - doesn't need project_id
        if self._router.has_v2:
            # Let resource-level errors propagate - they are definitive answers
            data = await self._v2_client.get_task(task_id)  # type: ignore
            return Task.from_v2(data)

        # Use V1 if V2 unavailable (requires project_id)
        if self._router.has_v1 and project_id:
            data = await self._v1_client.get_task(project_id, task_id)  # type: ignore
            return Task.from_v1(data)

        # No API available for this operation
        raise TickTickAPIUnavailableError(
            "Could not get task: V2 unavailable and V1 requires project_id",
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

        Raises:
            TickTickConfigurationError: If recurrence given without start_date
            TickTickAPIUnavailableError: If V2 API is not available
        """
        self._ensure_initialized()

        # Validate: recurrence requires start_date (TickTick silently ignores it otherwise)
        if repeat_flag and not start_date:
            raise TickTickConfigurationError(
                "Recurrence (repeat_flag) requires start_date. "
                "TickTick silently ignores recurrence without a start date."
            )

        # Default to inbox if no project specified
        if project_id is None:
            project_id = self._inbox_id
        if project_id is None:
            raise TickTickConfigurationError("No project ID provided and inbox ID unknown")

        # Format dates
        start_str = Task.format_datetime(start_date, "v2") if start_date else None
        due_str = Task.format_datetime(due_date, "v2") if due_date else None

        # V2 is REQUIRED (not optional fallback)
        if not self._router.has_v2:
            raise TickTickAPIUnavailableError(
                "V2 API is required for create_task but not available",
                operation="create_task",
            )

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
            # Note: parent_id is NOT passed here - V2 API ignores it during creation
            # We set it separately below via set_task_parent
        )

        # Get the created task ID from response
        task_id = next(iter(response.get("id2etag", {}).keys()), None)
        if not task_id:
            raise TickTickAPIError(
                "V2 create_task succeeded but returned no task ID",
                details={"response": response},
            )

        # If parent_id provided, set parent-child relationship separately
        # (V2 API ignores parentId during task creation)
        if parent_id:
            await self._v2_client.set_task_parent(task_id, project_id, parent_id)  # type: ignore

        return await self.get_task(task_id, project_id)

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

        Raises:
            TickTickNotFoundError: If the task does not exist
            TickTickAPIError: On other API errors
        """
        self._ensure_initialized()

        # Use V2 (primary)
        if self._router.has_v2:
            data = task.to_v2_dict(for_update=True)
            response = await self._v2_client.batch_tasks(update=[data])  # type: ignore

            # Check for errors in batch response
            _check_batch_response_errors(response, "update_task", [task.id])

            # Return updated task
            return await self.get_task(task.id, task.project_id)

        # Use V1 if V2 unavailable
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

        Uses V2 API primarily (better error handling).
        Falls back to V1 only if V2 unavailable.

        Note: V2 batch operations silently accept updates to nonexistent tasks,
        so we verify the task exists first to provide proper error handling.

        Args:
            task_id: Task ID
            project_id: Project ID

        Raises:
            TickTickNotFoundError: If the task does not exist
        """
        self._ensure_initialized()

        # Use V2 (primary) - better error handling
        if self._router.has_v2:
            # V2 batch API silently accepts updates to nonexistent tasks (returns
            # empty etag but no error). Verify task exists first for proper errors.
            await self._v2_client.get_task(task_id)  # type: ignore  # Raises NotFoundError if missing

            response = await self._v2_client.batch_tasks(  # type: ignore
                update=[{
                    "id": task_id,
                    "projectId": project_id,
                    "status": TaskStatus.COMPLETED,
                    "completedTime": Task.format_datetime(datetime.now(), "v2"),
                }]
            )
            # Check for errors in batch response (shouldn't happen after verify)
            _check_batch_response_errors(response, "complete_task", [task_id])
            return

        # Fallback to V1 only if V2 unavailable
        if self._router.has_v1:
            await self._v1_client.complete_task(project_id, task_id)  # type: ignore
            return

        raise TickTickAPIUnavailableError(
            "Could not complete task",
            operation="complete_task",
        )

    async def delete_task(self, task_id: str, project_id: str) -> None:
        """
        Delete a task.

        Note: V2 batch operations silently ignore nonexistent tasks,
        so we verify the task exists first to provide proper error handling.

        Args:
            task_id: Task ID
            project_id: Project ID

        Raises:
            TickTickNotFoundError: If the task does not exist
        """
        self._ensure_initialized()

        # Use V2 (primary)
        if self._router.has_v2:
            # V2 delete silently ignores nonexistent tasks. Verify first.
            await self._v2_client.get_task(task_id)  # type: ignore  # Raises NotFoundError if missing

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

    async def list_abandoned_tasks(
        self,
        from_date: datetime,
        to_date: datetime,
        limit: int = 100,
    ) -> list[Task]:
        """
        List abandoned ("won't do") tasks in a date range.

        V2-only operation.

        Args:
            from_date: Start date
            to_date: End date
            limit: Maximum results

        Returns:
            List of abandoned tasks
        """
        self._ensure_initialized()
        data = await self._v2_client.get_abandoned_tasks(from_date, to_date, limit)  # type: ignore
        return [Task.from_v2(t) for t in data]

    async def list_deleted_tasks(
        self,
        start: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """
        List deleted tasks (in trash).

        V2-only operation.

        Args:
            start: Pagination offset
            limit: Maximum results

        Returns:
            List of deleted tasks
        """
        self._ensure_initialized()
        data = await self._v2_client.get_deleted_tasks(start, limit)  # type: ignore
        return [Task.from_v2(t) for t in data.get("tasks", [])]

    async def move_task(
        self,
        task_id: str,
        from_project_id: str,
        to_project_id: str,
    ) -> None:
        """
        Move a task to a different project.

        V2-only operation.

        Note: V2 move operation silently ignores nonexistent tasks,
        so we verify the task exists first to provide proper error handling.

        Args:
            task_id: Task ID
            from_project_id: Source project ID
            to_project_id: Destination project ID

        Raises:
            TickTickNotFoundError: If the task does not exist
        """
        self._ensure_initialized()
        # V2 move silently ignores nonexistent tasks. Verify first.
        await self._v2_client.get_task(task_id)  # type: ignore  # Raises NotFoundError if missing
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

        Note: V2 set_parent operation silently ignores nonexistent tasks,
        so we verify the task exists first to provide proper error handling.

        Args:
            task_id: Task to make a subtask
            project_id: Project ID
            parent_id: Parent task ID

        Raises:
            TickTickNotFoundError: If the task does not exist
        """
        self._ensure_initialized()
        # V2 set_parent silently ignores nonexistent tasks. Verify first.
        await self._v2_client.get_task(task_id)  # type: ignore  # Raises NotFoundError if missing
        await self._v2_client.set_task_parent(task_id, project_id, parent_id)  # type: ignore

    async def unset_task_parent(
        self,
        task_id: str,
        project_id: str,
    ) -> None:
        """
        Remove a task from being a subtask (make it top-level).

        V2-only operation.

        Note: V2 unset_parent operation silently ignores nonexistent tasks,
        so we verify the task exists first to provide proper error handling.

        Args:
            task_id: Task to unparent
            project_id: Project ID

        Raises:
            TickTickNotFoundError: If the task does not exist
            TickTickAPIError: If the task is not a subtask
        """
        self._ensure_initialized()
        # V2 unset_parent silently ignores nonexistent tasks. Verify first.
        task = await self._v2_client.get_task(task_id)  # type: ignore  # Raises NotFoundError if missing

        # Check if it's actually a subtask
        parent_id = task.get("parentId")
        if not parent_id:
            raise TickTickAPIError(
                f"Task {task_id} is not a subtask (has no parent)",
                details={"task_id": task_id},
            )

        await self._v2_client.unset_task_parent(task_id, project_id, parent_id)  # type: ignore

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

        Raises:
            TickTickNotFoundError: If the project does not exist
        """
        self._ensure_initialized()

        # Use V2 (primary) - requires sync to get project list
        if self._router.has_v2:
            state = await self._v2_client.sync()  # type: ignore
            for p in state.get("projectProfiles", []):
                if p.get("id") == project_id:
                    return Project.from_v2(p)
            # Project not found in V2 sync response
            raise TickTickNotFoundError(
                f"Project not found: {project_id}",
                resource_id=project_id,
            )

        # Use V1 if V2 unavailable - has dedicated endpoint
        if self._router.has_v1:
            data = await self._v1_client.get_project(project_id)  # type: ignore
            return Project.from_v1(data)

        raise TickTickAPIUnavailableError(
            "Could not get project",
            operation="get_project",
        )

    async def get_project_with_data(self, project_id: str) -> ProjectData:
        """
        Get a project with its tasks and columns.

        Tries V2 API first (using sync data to get tasks), then falls back to V1.
        Note: V2 doesn't provide kanban column data, so columns will be empty.

        Args:
            project_id: Project ID

        Returns:
            ProjectData with project, tasks, and columns

        Raises:
            TickTickNotFoundError: If the project does not exist
        """
        self._ensure_initialized()

        # Try V2 first (more reliable for projects created via V2)
        if self._router.has_v2:
            try:
                # Get all data from sync
                state = await self._v2_client.sync()  # type: ignore

                # Find the project
                project_data = None
                for p in state.get("projectProfiles", []):
                    if p.get("id") == project_id:
                        project_data = p
                        break

                if project_data is None:
                    raise TickTickNotFoundError(
                        f"Project not found: {project_id}",
                        resource_id=project_id,
                    )

                project = Project.from_v2(project_data)

                # Get tasks for this project from sync data
                all_tasks_data = state.get("syncTaskBean", {}).get("update", [])
                project_tasks = [
                    Task.from_v2(t)
                    for t in all_tasks_data
                    if t.get("projectId") == project_id
                ]

                return ProjectData.from_v2(project, project_tasks)

            except TickTickNotFoundError:
                raise
            except Exception as e:
                logger.warning("V2 get_project_with_data failed, trying V1: %s", e)

        # Fall back to V1 if available
        if self._router.has_v1:
            try:
                data = await self._v1_client.get_project_with_data(project_id)  # type: ignore

                # V1 returns empty dict {} for nonexistent projects
                if not data or not data.get("project"):
                    raise TickTickNotFoundError(
                        f"Project not found: {project_id}",
                        resource_id=project_id,
                    )

                return ProjectData.from_v1(data)
            except TickTickNotFoundError:
                raise
            except Exception as e:
                logger.warning("V1 get_project_with_data also failed: %s", e)

        raise TickTickAPIUnavailableError(
            "Could not get project with data: both V1 and V2 failed",
            operation="get_project_with_data",
        )

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

        Raises:
            TickTickAPIUnavailableError: If V2 API is not available
        """
        self._ensure_initialized()

        # V2 is REQUIRED
        if not self._router.has_v2:
            raise TickTickAPIUnavailableError(
                "V2 API is required for create_project but not available",
                operation="create_project",
            )

        response = await self._v2_client.create_project(  # type: ignore
            name=name,
            color=color,
            kind=kind,
            view_mode=view_mode,
            group_id=group_id,
        )
        project_id = next(iter(response.get("id2etag", {}).keys()), None)
        if not project_id:
            raise TickTickAPIError(
                "V2 create_project succeeded but returned no project ID",
                details={"response": response},
            )

        return await self.get_project(project_id)

    async def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        color: str | None = None,
        folder_id: str | None = None,
    ) -> Project:
        """
        Update a project.

        V2-only operation.

        Args:
            project_id: Project ID
            name: New name (required)
            color: New hex color
            folder_id: New folder ID (use "NONE" to ungroup)

        Returns:
            Updated project

        Raises:
            TickTickNotFoundError: If the project does not exist
        """
        self._ensure_initialized()

        # Verify project exists first
        existing = await self.get_project(project_id)

        # Use existing name if not provided
        project_name = name if name is not None else existing.name

        await self._v2_client.update_project(  # type: ignore
            project_id=project_id,
            name=project_name,
            color=color,
            group_id=folder_id,
        )

        return await self.get_project(project_id)

    async def delete_project(self, project_id: str) -> None:
        """
        Delete a project.

        Note: V2 delete silently ignores nonexistent projects,
        so we verify the project exists first to provide proper error handling.

        Args:
            project_id: Project ID

        Raises:
            TickTickNotFoundError: If the project does not exist
        """
        self._ensure_initialized()

        # Use V2 (primary)
        if self._router.has_v2:
            # V2 delete silently ignores nonexistent projects. Verify first.
            await self.get_project(project_id)  # Raises NotFoundError if missing
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
        groups_data = state.get("projectGroups") or []  # Handle None values
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

    async def update_project_group(
        self,
        group_id: str,
        name: str,
    ) -> ProjectGroup:
        """
        Update a project group/folder (rename).

        V2-only operation.

        Args:
            group_id: Group ID
            name: New name

        Returns:
            Updated group

        Raises:
            TickTickNotFoundError: If the group does not exist
        """
        self._ensure_initialized()

        # Verify group exists first
        groups = await self.list_project_groups()
        existing = next((g for g in groups if g.id == group_id), None)
        if not existing:
            raise TickTickNotFoundError(
                f"Project group not found: {group_id}",
                resource_id=group_id,
            )

        await self._v2_client.update_project_group(group_id, name)  # type: ignore

        # Get updated group
        groups = await self.list_project_groups()
        for group in groups:
            if group.id == group_id:
                return group

        # Return with new name if not found (shouldn't happen)
        return ProjectGroup(id=group_id, name=name)

    async def delete_project_group(self, group_id: str) -> None:
        """
        Delete a project group/folder.

        V2-only operation.

        Note: V2 delete silently ignores nonexistent groups,
        so we verify the group exists first to provide proper error handling.

        Args:
            group_id: Group ID

        Raises:
            TickTickNotFoundError: If the group does not exist
        """
        self._ensure_initialized()

        # V2 delete silently ignores nonexistent groups. Verify first.
        groups = await self.list_project_groups()
        if not any(g.id == group_id for g in groups):
            raise TickTickNotFoundError(
                f"Project group not found: {group_id}",
                resource_id=group_id,
            )

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

    async def update_tag(
        self,
        name: str,
        *,
        color: str | None = None,
        parent: str | None = None,
    ) -> Tag:
        """
        Update a tag's properties (color, parent).

        V2-only operation.

        Args:
            name: Tag name (lowercase identifier)
            color: New hex color
            parent: New parent tag name (or None to remove parent)

        Returns:
            Updated tag

        Raises:
            TickTickNotFoundError: If the tag does not exist
        """
        self._ensure_initialized()

        # Verify tag exists first
        tags = await self.list_tags()
        existing = next((t for t in tags if t.name == name), None)
        if not existing:
            raise TickTickNotFoundError(
                f"Tag not found: {name}",
                resource_id=name,
            )

        # Use existing label
        await self._v2_client.update_tag(  # type: ignore
            name=name,
            label=existing.label,
            color=color,
            parent=parent,
        )

        # Get updated tag
        tags = await self.list_tags()
        for tag in tags:
            if tag.name == name:
                return tag

        # Return existing with updated fields if not found
        return Tag(
            name=name,
            label=existing.label,
            color=color or existing.color,
            parent=parent if parent is not None else existing.parent,
        )

    async def delete_tag(self, name: str) -> None:
        """
        Delete a tag.

        V2-only operation.

        Note: V2 delete silently ignores nonexistent tags,
        so we verify the tag exists first to provide proper error handling.

        Args:
            name: Tag name (lowercase identifier)

        Raises:
            TickTickNotFoundError: If the tag does not exist
        """
        self._ensure_initialized()

        # V2 delete silently ignores nonexistent tags. Verify first.
        tags = await self.list_tags()
        if not any(t.name == name for t in tags):
            raise TickTickNotFoundError(
                f"Tag not found: {name}",
                resource_id=name,
            )

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

    async def get_user_preferences(self) -> dict[str, Any]:
        """
        Get user preferences and settings.

        V2-only operation.

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
        self._ensure_initialized()
        return await self._v2_client.get_user_preferences()  # type: ignore

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

    # =========================================================================
    # Habit Operations (V2 Only)
    # =========================================================================

    async def list_habits(self) -> list[Habit]:
        """
        List all habits.

        V2-only operation.

        Returns:
            List of habits
        """
        self._ensure_initialized()
        data = await self._v2_client.get_habits()  # type: ignore
        return [Habit.from_v2(h) for h in data]

    async def get_habit(self, habit_id: str) -> Habit:
        """
        Get a habit by ID.

        V2-only operation.

        Args:
            habit_id: Habit ID

        Returns:
            Habit object

        Raises:
            TickTickNotFoundError: If habit not found
        """
        self._ensure_initialized()
        habits = await self.list_habits()
        for habit in habits:
            if habit.id == habit_id:
                return habit
        raise TickTickNotFoundError(
            f"Habit not found: {habit_id}",
            resource_id=habit_id,
        )

    async def list_habit_sections(self) -> list[HabitSection]:
        """
        List habit sections (time-of-day groupings).

        V2-only operation.

        Returns:
            List of habit sections (_morning, _afternoon, _night)
        """
        self._ensure_initialized()
        data = await self._v2_client.get_habit_sections()  # type: ignore
        return [HabitSection.from_v2(s) for s in data]

    async def get_habit_preferences(self) -> HabitPreferences:
        """
        Get habit preferences/settings.

        V2-only operation.

        Returns:
            Habit preferences (showInCalendar, showInToday, enabled, etc.)
        """
        self._ensure_initialized()
        data = await self._v2_client.get_habit_preferences()  # type: ignore
        return HabitPreferences.from_v2(data)

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

        V2-only operation.

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
        import secrets
        from datetime import datetime

        self._ensure_initialized()

        # Generate a 24-character hex ID (MongoDB ObjectId format)
        habit_id = secrets.token_hex(12)

        # Calculate target start date if target_days > 0
        target_start_date = None
        if target_days > 0:
            target_start_date = int(datetime.now().strftime("%Y%m%d"))

        # Determine if record_enable should be true (for numeric habits)
        record_enable = habit_type == "Real"

        response = await self._v2_client.create_habit(  # type: ignore
            habit_id=habit_id,
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
            target_start_date=target_start_date,
            encouragement=encouragement,
            record_enable=record_enable,
        )

        # Check for errors
        _check_batch_response_errors(response, "create_habit", [habit_id])

        # Return the created habit
        return await self.get_habit(habit_id)

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

        V2-only operation.

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
        self._ensure_initialized()

        # Verify habit exists
        await self.get_habit(habit_id)  # Raises NotFoundError if missing

        response = await self._v2_client.update_habit(  # type: ignore
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

        _check_batch_response_errors(response, "update_habit", [habit_id])

        return await self.get_habit(habit_id)

    async def delete_habit(self, habit_id: str) -> None:
        """
        Delete a habit.

        V2-only operation.

        Args:
            habit_id: Habit ID

        Raises:
            TickTickNotFoundError: If habit not found
        """
        self._ensure_initialized()

        # Verify habit exists
        await self.get_habit(habit_id)  # Raises NotFoundError if missing

        response = await self._v2_client.delete_habit(habit_id)  # type: ignore
        _check_batch_response_errors(response, "delete_habit", [habit_id])

    async def checkin_habit(
        self,
        habit_id: str,
        value: float = 1.0,
    ) -> Habit:
        """
        Check in a habit (complete it for today).

        V2-only operation.

        This increments the habit's totalCheckIns and currentStreak.

        Args:
            habit_id: Habit ID
            value: Check-in value (1.0 for boolean habits)

        Returns:
            Updated habit with preserved name and updated counters

        Raises:
            TickTickNotFoundError: If habit not found
        """
        self._ensure_initialized()

        # Get current habit to know current stats AND preserve its data
        # (The API may return habits with null names after update operations)
        original_habit = await self.get_habit(habit_id)

        # Use update_habit directly instead of checkin_habit to preserve the name
        # (The API nullifies fields that aren't sent in update operations)
        response = await self._v2_client.update_habit(  # type: ignore
            habit_id=habit_id,
            name=original_habit.name,  # Preserve name!
            total_checkins=original_habit.total_checkins + int(value),
            current_streak=original_habit.current_streak + 1,
        )

        _check_batch_response_errors(response, "checkin_habit", [habit_id])

        # Return a habit with updated counters but preserved original data
        # This avoids the issue where the API returns null for name after updates
        return Habit(
            id=original_habit.id,
            name=original_habit.name,
            icon=original_habit.icon,
            color=original_habit.color,
            sort_order=original_habit.sort_order,
            status=original_habit.status,
            encouragement=original_habit.encouragement,
            total_checkins=original_habit.total_checkins + int(value),
            created_time=original_habit.created_time,
            modified_time=original_habit.modified_time,
            archived_time=original_habit.archived_time,
            habit_type=original_habit.habit_type,
            goal=original_habit.goal,
            step=original_habit.step,
            unit=original_habit.unit,
            etag=original_habit.etag,
            repeat_rule=original_habit.repeat_rule,
            reminders=original_habit.reminders,
            record_enable=original_habit.record_enable,
            section_id=original_habit.section_id,
            target_days=original_habit.target_days,
            target_start_date=original_habit.target_start_date,
            completed_cycles=original_habit.completed_cycles,
            ex_dates=original_habit.ex_dates,
            current_streak=original_habit.current_streak + 1,
            style=original_habit.style,
        )

    async def archive_habit(self, habit_id: str) -> Habit:
        """
        Archive a habit.

        V2-only operation.

        Args:
            habit_id: Habit ID

        Returns:
            Updated habit with preserved data and archived status

        Raises:
            TickTickNotFoundError: If habit not found
        """
        from datetime import datetime

        self._ensure_initialized()

        # Get original habit data to preserve
        original_habit = await self.get_habit(habit_id)

        # Use update_habit directly instead of archive_habit to preserve the name
        # (The API nullifies fields that aren't sent in update operations)
        response = await self._v2_client.update_habit(  # type: ignore
            habit_id=habit_id,
            name=original_habit.name,  # Preserve name!
            status=2,  # Archived
        )
        _check_batch_response_errors(response, "archive_habit", [habit_id])

        # Return habit with preserved data and updated status
        return Habit(
            id=original_habit.id,
            name=original_habit.name,
            icon=original_habit.icon,
            color=original_habit.color,
            sort_order=original_habit.sort_order,
            status=2,  # Archived status
            encouragement=original_habit.encouragement,
            total_checkins=original_habit.total_checkins,
            created_time=original_habit.created_time,
            modified_time=datetime.now(),
            archived_time=datetime.now(),
            habit_type=original_habit.habit_type,
            goal=original_habit.goal,
            step=original_habit.step,
            unit=original_habit.unit,
            etag=original_habit.etag,
            repeat_rule=original_habit.repeat_rule,
            reminders=original_habit.reminders,
            record_enable=original_habit.record_enable,
            section_id=original_habit.section_id,
            target_days=original_habit.target_days,
            target_start_date=original_habit.target_start_date,
            completed_cycles=original_habit.completed_cycles,
            ex_dates=original_habit.ex_dates,
            current_streak=original_habit.current_streak,
            style=original_habit.style,
        )

    async def unarchive_habit(self, habit_id: str) -> Habit:
        """
        Unarchive a habit.

        V2-only operation.

        Args:
            habit_id: Habit ID

        Returns:
            Updated habit with preserved data and active status

        Raises:
            TickTickNotFoundError: If habit not found
        """
        from datetime import datetime

        self._ensure_initialized()

        # Get original habit data to preserve
        original_habit = await self.get_habit(habit_id)

        # Use update_habit directly instead of unarchive_habit to preserve the name
        # (The API nullifies fields that aren't sent in update operations)
        response = await self._v2_client.update_habit(  # type: ignore
            habit_id=habit_id,
            name=original_habit.name,  # Preserve name!
            status=0,  # Active
        )
        _check_batch_response_errors(response, "unarchive_habit", [habit_id])

        # Return habit with preserved data and active status
        return Habit(
            id=original_habit.id,
            name=original_habit.name,
            icon=original_habit.icon,
            color=original_habit.color,
            sort_order=original_habit.sort_order,
            status=0,  # Active status
            encouragement=original_habit.encouragement,
            total_checkins=original_habit.total_checkins,
            created_time=original_habit.created_time,
            modified_time=datetime.now(),
            archived_time=None,  # Clear archived time
            habit_type=original_habit.habit_type,
            goal=original_habit.goal,
            step=original_habit.step,
            unit=original_habit.unit,
            etag=original_habit.etag,
            repeat_rule=original_habit.repeat_rule,
            reminders=original_habit.reminders,
            record_enable=original_habit.record_enable,
            section_id=original_habit.section_id,
            target_days=original_habit.target_days,
            target_start_date=original_habit.target_start_date,
            completed_cycles=original_habit.completed_cycles,
            ex_dates=original_habit.ex_dates,
            current_streak=original_habit.current_streak,
            style=original_habit.style,
        )

    async def get_habit_checkins(
        self,
        habit_ids: list[str],
        after_stamp: int = 0,
    ) -> dict[str, list[HabitCheckin]]:
        """
        Get habit check-in data.

        V2-only operation.

        Args:
            habit_ids: List of habit IDs to query
            after_stamp: Date stamp (YYYYMMDD) to get check-ins after (0 for all)

        Returns:
            Dict mapping habit IDs to lists of check-in records
        """
        self._ensure_initialized()
        data = await self._v2_client.get_habit_checkins(habit_ids, after_stamp)  # type: ignore

        result: dict[str, list[HabitCheckin]] = {}
        checkins_data = data.get("checkins", {})

        for habit_id, checkins in checkins_data.items():
            result[habit_id] = [HabitCheckin.from_v2(c) for c in checkins]

        return result

"""
TickTick V1 API Client.

This module implements the client for TickTick's official V1 Open API.
It provides methods for all documented V1 endpoints.

Endpoints:
    Tasks:
        - GET /project/{projectId}/task/{taskId}
        - POST /task
        - POST /task/{taskId}
        - POST /project/{projectId}/task/{taskId}/complete
        - DELETE /project/{projectId}/task/{taskId}

    Projects:
        - GET /project
        - GET /project/{projectId}
        - GET /project/{projectId}/data
        - POST /project
        - POST /project/{projectId}
        - DELETE /project/{projectId}
"""

from __future__ import annotations

import logging
from typing import Any

from ticktick_mcp.api.base import BaseTickTickClient
from ticktick_mcp.api.v1.auth import OAuth2Handler, OAuth2Token
from ticktick_mcp.api.v1.types import (
    ProjectCreateV1,
    ProjectDataV1,
    ProjectUpdateV1,
    ProjectV1,
    TaskCreateV1,
    TaskUpdateV1,
    TaskV1,
)
from ticktick_mcp.constants import (
    APIVersion,
    DEFAULT_TIMEOUT,
    TICKTICK_API_BASE_V1,
)
from ticktick_mcp.exceptions import TickTickAuthenticationError

logger = logging.getLogger(__name__)


class TickTickV1Client(BaseTickTickClient):
    """
    Client for TickTick V1 Open API.

    This client handles OAuth2 authentication and provides methods
    for all V1 API endpoints.

    Usage:
        # With OAuth2 flow
        client = TickTickV1Client(
            client_id="your_client_id",
            client_secret="your_client_secret",
            redirect_uri="http://localhost:8080/callback",
        )

        # Get auth URL and exchange code
        auth_url, state = client.get_authorization_url()
        # ... user authorizes ...
        await client.authenticate_with_code(code, state)

        # Or with pre-obtained token
        client = TickTickV1Client(...)
        client.set_access_token("your_access_token")

        # Use the client
        async with client:
            projects = await client.get_projects()
            task = await client.create_task(title="Test", project_id=projects[0]["id"])
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        access_token: str | None = None,
        scopes: list[str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(timeout=timeout)

        self._oauth = OAuth2Handler(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes,
            timeout=timeout,
        )

        # Set pre-obtained token if provided
        if access_token:
            self._oauth.set_access_token(access_token)

    # =========================================================================
    # Abstract Property Implementations
    # =========================================================================

    @property
    def api_version(self) -> APIVersion:
        """Return the API version."""
        return APIVersion.V1

    @property
    def base_url(self) -> str:
        """Return the base URL for V1 API."""
        return TICKTICK_API_BASE_V1

    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated with a valid token."""
        return self._oauth.is_authenticated

    def _get_auth_headers(self) -> dict[str, str]:
        """Get OAuth2 authorization headers."""
        if self._oauth.token is None:
            return {}
        return {"Authorization": self._oauth.token.authorization_header}

    # =========================================================================
    # Authentication Methods
    # =========================================================================

    def get_authorization_url(self, state: str | None = None) -> tuple[str, str]:
        """
        Get the OAuth2 authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Tuple of (authorization_url, state)
        """
        return self._oauth.get_authorization_url(state)

    async def authenticate_with_code(
        self,
        code: str,
        state: str | None = None,
    ) -> OAuth2Token:
        """
        Authenticate by exchanging an authorization code for a token.

        Args:
            code: Authorization code from callback
            state: State parameter for verification

        Returns:
            OAuth2Token with access credentials
        """
        return await self._oauth.exchange_code(code, state)

    async def refresh_token(self) -> OAuth2Token:
        """
        Refresh the access token.

        Returns:
            OAuth2Token with new credentials
        """
        return await self._oauth.refresh_access_token()

    def set_access_token(self, access_token: str) -> None:
        """
        Set an access token directly.

        Args:
            access_token: Pre-obtained OAuth2 access token
        """
        self._oauth.set_access_token(access_token)

    def get_access_token(self) -> str | None:
        """Get the current access token."""
        return self._oauth.access_token

    @property
    def token(self) -> OAuth2Token | None:
        """Get the current OAuth2 token object."""
        return self._oauth.token

    # =========================================================================
    # Task Endpoints
    # =========================================================================

    async def get_task(self, project_id: str, task_id: str) -> TaskV1:
        """
        Get a task by project ID and task ID.

        Args:
            project_id: Project identifier
            task_id: Task identifier

        Returns:
            Task data
        """
        endpoint = f"/project/{project_id}/task/{task_id}"
        response = await self._get_json(endpoint)
        return response

    async def create_task(
        self,
        title: str,
        project_id: str,
        *,
        content: str | None = None,
        desc: str | None = None,
        is_all_day: bool | None = None,
        start_date: str | None = None,
        due_date: str | None = None,
        time_zone: str | None = None,
        reminders: list[str] | None = None,
        repeat_flag: str | None = None,
        priority: int | None = None,
        sort_order: int | None = None,
        items: list[dict[str, Any]] | None = None,
    ) -> TaskV1:
        """
        Create a new task.

        Args:
            title: Task title (required)
            project_id: Project ID (required)
            content: Task content/description
            desc: Checklist description
            is_all_day: Whether the task is an all-day event
            start_date: Start date in ISO format
            due_date: Due date in ISO format
            time_zone: IANA timezone name
            reminders: List of reminder triggers
            repeat_flag: RRULE recurrence rule
            priority: Priority (0=none, 1=low, 3=medium, 5=high)
            sort_order: Sort order value
            items: Subtask/checklist items

        Returns:
            Created task data
        """
        data: TaskCreateV1 = {
            "title": title,
            "projectId": project_id,
        }

        if content is not None:
            data["content"] = content
        if desc is not None:
            data["desc"] = desc
        if is_all_day is not None:
            data["isAllDay"] = is_all_day
        if start_date is not None:
            data["startDate"] = start_date
        if due_date is not None:
            data["dueDate"] = due_date
        if time_zone is not None:
            data["timeZone"] = time_zone
        if reminders is not None:
            data["reminders"] = reminders
        if repeat_flag is not None:
            data["repeatFlag"] = repeat_flag
        if priority is not None:
            data["priority"] = priority
        if sort_order is not None:
            data["sortOrder"] = sort_order
        if items is not None:
            data["items"] = items  # type: ignore

        response = await self._post_json("/task", json_data=data)
        return response

    async def update_task(
        self,
        task_id: str,
        project_id: str,
        *,
        title: str | None = None,
        content: str | None = None,
        desc: str | None = None,
        is_all_day: bool | None = None,
        start_date: str | None = None,
        due_date: str | None = None,
        time_zone: str | None = None,
        reminders: list[str] | None = None,
        repeat_flag: str | None = None,
        priority: int | None = None,
        sort_order: int | None = None,
        items: list[dict[str, Any]] | None = None,
    ) -> TaskV1:
        """
        Update an existing task.

        Args:
            task_id: Task identifier (required)
            project_id: Project identifier (required)
            title: New title
            content: New content
            desc: New description
            is_all_day: All-day flag
            start_date: New start date
            due_date: New due date
            time_zone: New timezone
            reminders: New reminders
            repeat_flag: New recurrence rule
            priority: New priority
            sort_order: New sort order
            items: New subtask items

        Returns:
            Updated task data
        """
        data: TaskUpdateV1 = {
            "id": task_id,
            "projectId": project_id,
        }

        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        if desc is not None:
            data["desc"] = desc
        if is_all_day is not None:
            data["isAllDay"] = is_all_day
        if start_date is not None:
            data["startDate"] = start_date
        if due_date is not None:
            data["dueDate"] = due_date
        if time_zone is not None:
            data["timeZone"] = time_zone
        if reminders is not None:
            data["reminders"] = reminders
        if repeat_flag is not None:
            data["repeatFlag"] = repeat_flag
        if priority is not None:
            data["priority"] = priority
        if sort_order is not None:
            data["sortOrder"] = sort_order
        if items is not None:
            data["items"] = items  # type: ignore

        endpoint = f"/task/{task_id}"
        response = await self._post_json(endpoint, json_data=data)
        return response

    async def complete_task(self, project_id: str, task_id: str) -> None:
        """
        Mark a task as complete.

        Args:
            project_id: Project identifier
            task_id: Task identifier
        """
        endpoint = f"/project/{project_id}/task/{task_id}/complete"
        await self._post(endpoint)

    async def delete_task(self, project_id: str, task_id: str) -> None:
        """
        Delete a task.

        Args:
            project_id: Project identifier
            task_id: Task identifier
        """
        endpoint = f"/project/{project_id}/task/{task_id}"
        await self._delete(endpoint)

    # =========================================================================
    # Project Endpoints
    # =========================================================================

    async def get_projects(self) -> list[ProjectV1]:
        """
        Get all user projects.

        Returns:
            List of projects
        """
        response = await self._get_json("/project")
        return response

    async def get_project(self, project_id: str) -> ProjectV1:
        """
        Get a project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project data
        """
        endpoint = f"/project/{project_id}"
        response = await self._get_json(endpoint)
        return response

    async def get_project_with_data(self, project_id: str) -> ProjectDataV1:
        """
        Get a project with its tasks and columns.

        This endpoint is unique to V1 and returns the complete project
        data including all tasks and kanban columns.

        Args:
            project_id: Project identifier

        Returns:
            Project data with tasks and columns
        """
        endpoint = f"/project/{project_id}/data"
        response = await self._get_json(endpoint)
        return response

    async def create_project(
        self,
        name: str,
        *,
        color: str | None = None,
        sort_order: int | None = None,
        view_mode: str | None = None,
        kind: str | None = None,
    ) -> ProjectV1:
        """
        Create a new project.

        Args:
            name: Project name (required)
            color: Hex color code (e.g., "#F18181")
            sort_order: Sort order value
            view_mode: View mode (list, kanban, timeline)
            kind: Project type (TASK, NOTE)

        Returns:
            Created project data
        """
        data: ProjectCreateV1 = {"name": name}

        if color is not None:
            data["color"] = color
        if sort_order is not None:
            data["sortOrder"] = sort_order
        if view_mode is not None:
            data["viewMode"] = view_mode
        if kind is not None:
            data["kind"] = kind

        response = await self._post_json("/project", json_data=data)
        return response

    async def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        color: str | None = None,
        sort_order: int | None = None,
        view_mode: str | None = None,
        kind: str | None = None,
    ) -> ProjectV1:
        """
        Update an existing project.

        Args:
            project_id: Project identifier
            name: New name
            color: New color
            sort_order: New sort order
            view_mode: New view mode
            kind: New project type

        Returns:
            Updated project data
        """
        data: ProjectUpdateV1 = {}

        if name is not None:
            data["name"] = name
        if color is not None:
            data["color"] = color
        if sort_order is not None:
            data["sortOrder"] = sort_order
        if view_mode is not None:
            data["viewMode"] = view_mode
        if kind is not None:
            data["kind"] = kind

        endpoint = f"/project/{project_id}"
        response = await self._post_json(endpoint, json_data=data)
        return response

    async def delete_project(self, project_id: str) -> None:
        """
        Delete a project.

        Args:
            project_id: Project identifier
        """
        endpoint = f"/project/{project_id}"
        await self._delete(endpoint)

    # =========================================================================
    # Health Check
    # =========================================================================

    async def verify_authentication(self) -> bool:
        """
        Verify that authentication is working by fetching projects.

        Returns:
            True if authentication is valid

        Raises:
            TickTickAuthenticationError: If not authenticated
        """
        if not self.is_authenticated:
            raise TickTickAuthenticationError(
                "V1 API not authenticated - no access token available"
            )

        try:
            # Try to fetch projects as a health check
            await self.get_projects()
            return True
        except TickTickAuthenticationError:
            raise
        except Exception as e:
            logger.warning("V1 authentication verification failed: %s", e)
            return False

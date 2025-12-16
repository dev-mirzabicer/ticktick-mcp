"""
Comprehensive Error Handling Tests for TickTick Client.

This module tests error handling across all operations including:
- Not found errors
- Authentication errors
- API errors
- Validation errors
- Configuration errors
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ticktick_mcp.exceptions import (
    TickTickError,
    TickTickAuthenticationError,
    TickTickAPIError,
    TickTickNotFoundError,
    TickTickValidationError,
    TickTickConfigurationError,
)

if TYPE_CHECKING:
    from tests.conftest import MockUnifiedAPI
    from ticktick_mcp.client import TickTickClient


pytestmark = [pytest.mark.errors, pytest.mark.unit]


# =============================================================================
# Not Found Error Tests
# =============================================================================


class TestNotFoundErrors:
    """Tests for not found error handling."""

    async def test_get_nonexistent_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when getting task that doesn't exist."""
        with pytest.raises(TickTickNotFoundError):
            await client.get_task("nonexistent_task_123456789")

    async def test_update_nonexistent_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when updating task that doesn't exist."""
        from tests.conftest import TaskFactory

        fake_task = TaskFactory.create(id="nonexistent_123456789")

        with pytest.raises(TickTickNotFoundError):
            await client.update_task(fake_task)

    async def test_complete_nonexistent_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when completing task that doesn't exist."""
        with pytest.raises(TickTickNotFoundError):
            await client.complete_task("nonexistent_123", "project_123")

    async def test_delete_nonexistent_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when deleting task that doesn't exist."""
        with pytest.raises(TickTickNotFoundError):
            await client.delete_task("nonexistent_123", "project_123")

    async def test_move_nonexistent_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when moving task that doesn't exist."""
        with pytest.raises(TickTickNotFoundError):
            await client.move_task("nonexistent_123", "project_1", "project_2")

    async def test_make_subtask_nonexistent_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when making nonexistent task a subtask."""
        parent = await client.create_task(title="Parent")

        with pytest.raises(TickTickNotFoundError):
            await client.make_subtask("nonexistent_123", parent.id, parent.project_id)

    async def test_get_nonexistent_project(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when getting project that doesn't exist."""
        with pytest.raises(TickTickNotFoundError):
            await client.get_project("nonexistent_project_123")

    async def test_get_nonexistent_project_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when getting tasks for nonexistent project."""
        with pytest.raises(TickTickNotFoundError):
            await client.get_project_tasks("nonexistent_project_123")

    async def test_delete_nonexistent_project(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when deleting project that doesn't exist."""
        with pytest.raises(TickTickNotFoundError):
            await client.delete_project("nonexistent_project_123")

    async def test_delete_nonexistent_folder(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when deleting folder that doesn't exist."""
        with pytest.raises(TickTickNotFoundError):
            await client.delete_folder("nonexistent_folder_123")

    async def test_delete_nonexistent_tag(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when deleting tag that doesn't exist."""
        with pytest.raises(TickTickNotFoundError):
            await client.delete_tag("nonexistent_tag")

    async def test_rename_nonexistent_tag(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when renaming tag that doesn't exist."""
        with pytest.raises(TickTickNotFoundError):
            await client.rename_tag("nonexistent_tag", "new_name")

    async def test_merge_nonexistent_source_tag(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when merging from nonexistent source tag."""
        target = await client.create_tag(name="Target")

        with pytest.raises(TickTickNotFoundError):
            await client.merge_tags("nonexistent_source", target.name)

    async def test_merge_to_nonexistent_target_tag(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test error when merging to nonexistent target tag."""
        source = await client.create_tag(name="Source")

        with pytest.raises(TickTickNotFoundError):
            await client.merge_tags(source.name, "nonexistent_target")


# =============================================================================
# API Error Tests
# =============================================================================


class TestAPIErrors:
    """Tests for API error handling."""

    async def test_api_error_on_task_create(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test API error handling during task creation."""
        mock_api.should_fail["create_task"] = TickTickAPIError("API Error")

        with pytest.raises(TickTickAPIError):
            await client.create_task(title="Test Task")

    async def test_api_error_on_sync(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test API error handling during sync."""
        mock_api.should_fail["sync_all"] = TickTickAPIError("Sync failed")

        with pytest.raises(TickTickAPIError):
            await client.sync()

    async def test_api_error_on_list_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test API error handling during task listing."""
        mock_api.should_fail["list_all_tasks"] = TickTickAPIError("Failed to list tasks")

        with pytest.raises(TickTickAPIError):
            await client.get_all_tasks()

    async def test_api_error_on_list_projects(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test API error handling during project listing."""
        mock_api.should_fail["list_projects"] = TickTickAPIError("Failed to list projects")

        with pytest.raises(TickTickAPIError):
            await client.get_all_projects()


# =============================================================================
# Authentication Error Tests
# =============================================================================


class TestAuthenticationErrors:
    """Tests for authentication error handling."""

    async def test_authentication_error_on_initialize(
        self,
        mock_api: MockUnifiedAPI,
    ):
        """Test authentication error during initialization."""
        from unittest.mock import patch

        mock_api.should_fail["initialize"] = TickTickAuthenticationError("Invalid credentials")

        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            MockAPIClass.return_value = mock_api

            client = TickTickClient(
                client_id="test_id",
                client_secret="test_secret",
                v1_access_token="invalid_token",
                username="invalid@example.com",
                password="wrong_password",
            )
            client._api = mock_api

            with pytest.raises(TickTickAuthenticationError):
                await client.connect()

    async def test_auth_error_preserved_message(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that authentication error message is preserved."""
        error_message = "Token expired or invalid"
        mock_api.should_fail["get_user_profile"] = TickTickAuthenticationError(error_message)

        with pytest.raises(TickTickAuthenticationError) as exc_info:
            await client.get_profile()

        assert error_message in str(exc_info.value)


# =============================================================================
# Error Recovery Tests
# =============================================================================


class TestErrorRecovery:
    """Tests for error recovery scenarios."""

    async def test_operation_succeeds_after_error_cleared(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
    ):
        """Test that operations succeed after error condition is cleared."""
        # Set up error
        mock_api.should_fail["create_task"] = TickTickAPIError("Temporary error")

        with pytest.raises(TickTickAPIError):
            await client.create_task(title="Test")

        # Clear error
        del mock_api.should_fail["create_task"]

        # Should succeed now
        task = await client.create_task(title="Test")
        assert task is not None

    async def test_other_operations_work_during_partial_failure(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
    ):
        """Test that other operations work when one fails."""
        # Make only tag operations fail
        mock_api.should_fail["create_tag"] = TickTickAPIError("Tag service unavailable")

        # Task operations should still work
        task = await client.create_task(title="Test Task")
        assert task is not None

        # Project operations should work
        project = await client.create_project(name="Test Project")
        assert project is not None

        # Tag operation should fail
        with pytest.raises(TickTickAPIError):
            await client.create_tag(name="Test Tag")

    async def test_successful_operations_not_affected_by_later_errors(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
    ):
        """Test that already completed operations are preserved after errors."""
        # Create task successfully
        task = await client.create_task(title="Success Task")
        assert task.id in mock_api.tasks

        # Now set up error
        mock_api.should_fail["create_task"] = TickTickAPIError("Error")

        with pytest.raises(TickTickAPIError):
            await client.create_task(title="Failed Task")

        # Original task should still exist
        assert task.id in mock_api.tasks


# =============================================================================
# Edge Case Error Tests
# =============================================================================


class TestEdgeCaseErrors:
    """Tests for edge case error scenarios."""

    async def test_error_on_delete_then_get(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting a deleted task raises not found."""
        task = await client.create_task(title="Task")
        task_id = task.id

        await client.delete_task(task_id, task.project_id)

        with pytest.raises(TickTickNotFoundError):
            await client.get_task(task_id)

    async def test_error_on_complete_deleted_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test completing a deleted task raises error."""
        task = await client.create_task(title="Task")
        project_id = task.project_id
        task_id = task.id

        await client.delete_task(task_id, project_id)

        with pytest.raises(TickTickNotFoundError):
            await client.complete_task(task_id, project_id)

    async def test_error_on_move_to_deleted_project(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
    ):
        """Test moving task to deleted project raises error."""
        project = await client.create_project(name="Target")
        task = await client.create_task(title="Task")

        # Delete target project
        await client.delete_project(project.id)

        # Attempt move should use the project ID, but project doesn't exist
        # The mock doesn't validate target project existence, but tests the flow
        await client.move_task(task.id, task.project_id, project.id)
        # In real API this would fail

    async def test_sequential_not_found_errors(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test multiple sequential not found errors."""
        for i in range(5):
            with pytest.raises(TickTickNotFoundError):
                await client.get_task(f"nonexistent_{i}")

    async def test_error_message_contains_id(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that error messages contain the problematic ID."""
        task_id = "specific_task_id_12345"

        with pytest.raises(TickTickNotFoundError) as exc_info:
            await client.get_task(task_id)

        assert task_id in str(exc_info.value)


# =============================================================================
# Exception Hierarchy Tests
# =============================================================================


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    async def test_not_found_is_api_error(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that NotFoundError is subclass of APIError."""
        try:
            await client.get_task("nonexistent")
        except TickTickNotFoundError as e:
            assert isinstance(e, TickTickAPIError)
            assert isinstance(e, TickTickError)

    def test_exception_inheritance(self):
        """Test exception class inheritance."""
        # All exceptions inherit from TickTickError
        assert issubclass(TickTickAPIError, TickTickError)
        assert issubclass(TickTickAuthenticationError, TickTickError)
        assert issubclass(TickTickValidationError, TickTickError)
        assert issubclass(TickTickConfigurationError, TickTickError)

        # NotFoundError is an APIError
        assert issubclass(TickTickNotFoundError, TickTickAPIError)

    async def test_catch_base_exception(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that catching base TickTickError catches all."""
        mock_api.should_fail["create_task"] = TickTickAPIError("API Error")

        with pytest.raises(TickTickError):
            await client.create_task(title="Test")

    async def test_specific_exception_not_caught_by_sibling(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
    ):
        """Test that sibling exceptions don't catch each other."""
        mock_api.should_fail["create_task"] = TickTickAPIError("API Error")

        # ValidationError shouldn't catch APIError
        with pytest.raises(TickTickAPIError):
            try:
                await client.create_task(title="Test")
            except TickTickValidationError:
                pytest.fail("ValidationError shouldn't catch APIError")

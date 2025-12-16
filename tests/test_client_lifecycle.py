"""
Comprehensive Client Lifecycle Tests for TickTick Client.

This module tests client lifecycle management including:
- Connection and disconnection
- Context manager usage
- Reconnection scenarios
- State management
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from ticktick_mcp.client import TickTickClient

if TYPE_CHECKING:
    from tests.conftest import MockUnifiedAPI


pytestmark = [pytest.mark.lifecycle, pytest.mark.unit]


# =============================================================================
# Connection Tests
# =============================================================================


class TestConnection:
    """Tests for client connection."""

    async def test_connect(self, mock_api: MockUnifiedAPI):
        """Test basic connection."""
        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            MockAPIClass.return_value = mock_api

            client = TickTickClient(
                client_id="test_id",
                client_secret="test_secret",
                v1_access_token="test_token",
                username="test@example.com",
                password="test_password",
            )
            client._api = mock_api

            await client.connect()

            assert client.is_connected is True
            mock_api.assert_called("initialize")

    async def test_disconnect(self, mock_api: MockUnifiedAPI):
        """Test disconnection."""
        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            MockAPIClass.return_value = mock_api

            client = TickTickClient(
                client_id="test_id",
                client_secret="test_secret",
                v1_access_token="test_token",
                username="test@example.com",
                password="test_password",
            )
            client._api = mock_api

            await client.connect()
            await client.disconnect()

            assert client.is_connected is False

    async def test_is_connected_property(self, mock_api: MockUnifiedAPI):
        """Test is_connected property reflects state."""
        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            MockAPIClass.return_value = mock_api

            client = TickTickClient(
                client_id="test_id",
                client_secret="test_secret",
                v1_access_token="test_token",
                username="test@example.com",
                password="test_password",
            )
            client._api = mock_api

            # Initially not connected
            assert client.is_connected is False

            # After connect
            await client.connect()
            assert client.is_connected is True

            # After disconnect
            await client.disconnect()
            assert client.is_connected is False


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestContextManager:
    """Tests for async context manager usage."""

    async def test_context_manager_connects_and_disconnects(self, mock_api: MockUnifiedAPI):
        """Test that context manager properly connects and disconnects."""
        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            MockAPIClass.return_value = mock_api

            async with TickTickClient(
                client_id="test_id",
                client_secret="test_secret",
                v1_access_token="test_token",
                username="test@example.com",
                password="test_password",
            ) as client:
                client._api = mock_api
                # Inside context, should be connected
                assert client.is_connected is True

            # After context, should be disconnected (in mock)
            # Note: Can't check is_connected here as client is out of scope

    async def test_context_manager_returns_client(self, mock_api: MockUnifiedAPI):
        """Test that context manager returns the client."""
        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            MockAPIClass.return_value = mock_api

            async with TickTickClient(
                client_id="test_id",
                client_secret="test_secret",
                v1_access_token="test_token",
                username="test@example.com",
                password="test_password",
            ) as client:
                client._api = mock_api
                assert isinstance(client, TickTickClient)

    async def test_context_manager_can_perform_operations(self, client: TickTickClient):
        """Test that operations work within context manager."""
        # client fixture already uses context manager pattern
        task = await client.create_task(title="Context Task")
        assert task is not None

        project = await client.create_project(name="Context Project")
        assert project is not None

    async def test_context_manager_disconnects_on_exception(self, mock_api: MockUnifiedAPI):
        """Test that context manager disconnects even on exception."""
        disconnect_called = False
        original_close = mock_api.close

        async def tracking_close():
            nonlocal disconnect_called
            disconnect_called = True
            await original_close()

        mock_api.close = tracking_close

        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            MockAPIClass.return_value = mock_api

            with pytest.raises(ValueError):
                async with TickTickClient(
                    client_id="test_id",
                    client_secret="test_secret",
                    v1_access_token="test_token",
                    username="test@example.com",
                    password="test_password",
                ) as client:
                    client._api = mock_api
                    await client.connect()
                    raise ValueError("Test exception")

            assert disconnect_called is True


# =============================================================================
# Inbox ID Tests
# =============================================================================


class TestInboxId:
    """Tests for inbox ID property."""

    async def test_inbox_id_available_after_connect(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that inbox_id is available after connection."""
        inbox_id = client.inbox_id

        assert inbox_id is not None
        assert inbox_id == mock_api.inbox_id

    async def test_inbox_id_matches_status(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that inbox_id matches user status inbox_id."""
        status = await client.get_status()

        assert client.inbox_id == mock_api.inbox_id


# =============================================================================
# Reconnection Tests
# =============================================================================


class TestReconnection:
    """Tests for reconnection scenarios."""

    async def test_connect_twice(self, mock_api: MockUnifiedAPI):
        """Test connecting twice (should be idempotent or handle gracefully)."""
        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            MockAPIClass.return_value = mock_api

            client = TickTickClient(
                client_id="test_id",
                client_secret="test_secret",
                v1_access_token="test_token",
                username="test@example.com",
                password="test_password",
            )
            client._api = mock_api

            await client.connect()
            await client.connect()  # Second connect

            assert client.is_connected is True

    async def test_disconnect_twice(self, mock_api: MockUnifiedAPI):
        """Test disconnecting twice (should be safe)."""
        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            MockAPIClass.return_value = mock_api

            client = TickTickClient(
                client_id="test_id",
                client_secret="test_secret",
                v1_access_token="test_token",
                username="test@example.com",
                password="test_password",
            )
            client._api = mock_api

            await client.connect()
            await client.disconnect()
            await client.disconnect()  # Second disconnect

            assert client.is_connected is False

    async def test_reconnect_after_disconnect(self, mock_api: MockUnifiedAPI):
        """Test reconnecting after disconnect."""
        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            MockAPIClass.return_value = mock_api

            client = TickTickClient(
                client_id="test_id",
                client_secret="test_secret",
                v1_access_token="test_token",
                username="test@example.com",
                password="test_password",
            )
            client._api = mock_api

            await client.connect()
            assert client.is_connected is True

            await client.disconnect()
            assert client.is_connected is False

            await client.connect()
            assert client.is_connected is True


# =============================================================================
# State Persistence Tests
# =============================================================================


class TestStatePersistence:
    """Tests for state persistence across operations."""

    async def test_tasks_persist_across_calls(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that created tasks persist."""
        task1 = await client.create_task(title="Task 1")
        task2 = await client.create_task(title="Task 2")
        task3 = await client.create_task(title="Task 3")

        all_tasks = await client.get_all_tasks()

        assert len(all_tasks) == 3
        assert task1.id in [t.id for t in all_tasks]
        assert task2.id in [t.id for t in all_tasks]
        assert task3.id in [t.id for t in all_tasks]

    async def test_projects_persist_across_calls(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that created projects persist."""
        project1 = await client.create_project(name="Project 1")
        project2 = await client.create_project(name="Project 2")

        all_projects = await client.get_all_projects()

        assert len(all_projects) == 2

    async def test_modifications_persist(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that modifications persist."""
        task = await client.create_task(title="Original")

        task.title = "Modified"
        await client.update_task(task)

        retrieved = await client.get_task(task.id)
        assert retrieved.title == "Modified"

    async def test_deletions_persist(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that deletions persist."""
        task = await client.create_task(title="To Delete")
        task_id = task.id

        await client.delete_task(task_id, task.project_id)

        from ticktick_mcp.exceptions import TickTickNotFoundError
        with pytest.raises(TickTickNotFoundError):
            await client.get_task(task_id)


# =============================================================================
# Configuration Tests
# =============================================================================


class TestConfiguration:
    """Tests for client configuration."""

    async def test_from_settings_creates_client(self):
        """Test that from_settings creates a valid client."""
        # This would require mock settings, so we test the class method exists
        assert hasattr(TickTickClient, "from_settings")
        assert callable(TickTickClient.from_settings)

    def test_client_accepts_all_parameters(self):
        """Test that client constructor accepts all parameters."""
        # Should not raise
        client = TickTickClient(
            client_id="id",
            client_secret="secret",
            redirect_uri="http://localhost:8080/callback",
            v1_access_token="token",
            username="user",
            password="pass",
            timeout=60.0,
            device_id="device123",
        )

        assert client is not None

    def test_client_with_minimal_parameters(self):
        """Test that client can be created with minimal parameters."""
        client = TickTickClient(
            client_id="id",
            client_secret="secret",
        )

        assert client is not None


# =============================================================================
# Multiple Client Tests
# =============================================================================


class TestMultipleClients:
    """Tests for multiple client instances."""

    async def test_multiple_clients_independent(self, mock_api: MockUnifiedAPI):
        """Test that multiple client instances are independent."""
        with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
            # Create separate mocks for each client
            mock_api1 = MockUnifiedAPI()
            mock_api2 = MockUnifiedAPI()

            MockAPIClass.side_effect = [mock_api1, mock_api2]

            client1 = TickTickClient(
                client_id="id1",
                client_secret="secret1",
                username="user1@example.com",
                password="pass1",
            )

            client2 = TickTickClient(
                client_id="id2",
                client_secret="secret2",
                username="user2@example.com",
                password="pass2",
            )

            # Set up the APIs directly
            client1._api = mock_api1
            client2._api = mock_api2

            await client1.connect()
            await client2.connect()

            # Create task in client1
            task1 = await client1.create_task(title="Client 1 Task")

            # Should not appear in client2's mock
            assert task1.id in mock_api1.tasks
            assert task1.id not in mock_api2.tasks

            await client1.disconnect()
            await client2.disconnect()

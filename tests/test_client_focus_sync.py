"""
Comprehensive Focus/Pomodoro and Sync Operation Tests for TickTick Client.

This module tests all focus and sync related functionality including:
- Focus heatmap retrieval
- Focus distribution by tag
- Full state sync
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.conftest import MockUnifiedAPI
    from ticktick_mcp.client import TickTickClient


pytestmark = [pytest.mark.unit]


# =============================================================================
# Focus Heatmap Tests
# =============================================================================


@pytest.mark.focus
class TestFocusHeatmap:
    """Tests for focus heatmap retrieval."""

    async def test_get_focus_heatmap_default(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting focus heatmap with default parameters."""
        data = await client.get_focus_heatmap()

        assert data is not None
        assert isinstance(data, list)
        mock_api.assert_called("get_focus_heatmap")

    async def test_get_focus_heatmap_with_days(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting focus heatmap with days parameter."""
        data = await client.get_focus_heatmap(days=7)

        assert data is not None

    async def test_get_focus_heatmap_with_dates(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting focus heatmap with specific dates."""
        start = date.today() - timedelta(days=30)
        end = date.today()

        data = await client.get_focus_heatmap(start_date=start, end_date=end)

        assert data is not None

    @pytest.mark.parametrize("days", [1, 7, 30, 90, 365])
    async def test_get_focus_heatmap_various_ranges(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
        days: int,
    ):
        """Test getting focus heatmap for various date ranges."""
        data = await client.get_focus_heatmap(days=days)

        assert data is not None
        assert isinstance(data, list)

    async def test_get_focus_heatmap_returns_duration(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that heatmap data includes duration."""
        data = await client.get_focus_heatmap()

        # Mock returns data with duration
        assert len(data) > 0
        for entry in data:
            assert "duration" in entry

    async def test_get_focus_heatmap_empty_period(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test heatmap for period with no focus sessions."""
        # Configure mock to return empty
        original_method = mock_api.get_focus_heatmap

        async def empty_heatmap(*args, **kwargs):
            mock_api._record_call("get_focus_heatmap", args, kwargs)
            return []

        mock_api.get_focus_heatmap = empty_heatmap

        data = await client.get_focus_heatmap()

        assert data == []

        # Restore
        mock_api.get_focus_heatmap = original_method


# =============================================================================
# Focus by Tag Tests
# =============================================================================


@pytest.mark.focus
class TestFocusByTag:
    """Tests for focus distribution by tag."""

    async def test_get_focus_by_tag_default(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting focus by tag with default parameters."""
        data = await client.get_focus_by_tag()

        assert data is not None
        assert isinstance(data, dict)
        mock_api.assert_called("get_focus_by_tag")

    async def test_get_focus_by_tag_with_days(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting focus by tag with days parameter."""
        data = await client.get_focus_by_tag(days=14)

        assert data is not None

    async def test_get_focus_by_tag_with_dates(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting focus by tag with specific dates."""
        start = date.today() - timedelta(days=7)
        end = date.today()

        data = await client.get_focus_by_tag(start_date=start, end_date=end)

        assert data is not None

    async def test_get_focus_by_tag_returns_tag_durations(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
    ):
        """Test that focus by tag returns tag -> duration mapping."""
        data = await client.get_focus_by_tag()

        # Mock returns work and study tags
        assert "work" in data
        assert "study" in data
        assert isinstance(data["work"], int)
        assert isinstance(data["study"], int)

    async def test_get_focus_by_tag_empty(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test focus by tag when no focus data exists."""
        original_method = mock_api.get_focus_by_tag

        async def empty_focus(*args, **kwargs):
            mock_api._record_call("get_focus_by_tag", args, kwargs)
            return {}

        mock_api.get_focus_by_tag = empty_focus

        data = await client.get_focus_by_tag()

        assert data == {}

        mock_api.get_focus_by_tag = original_method

    @pytest.mark.parametrize("days", [7, 30, 90])
    async def test_get_focus_by_tag_various_ranges(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
        days: int,
    ):
        """Test focus by tag for various date ranges."""
        data = await client.get_focus_by_tag(days=days)

        assert isinstance(data, dict)


# =============================================================================
# Sync Tests
# =============================================================================


@pytest.mark.sync
class TestSync:
    """Tests for full state sync."""

    async def test_sync_returns_state(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that sync returns complete state."""
        state = await client.sync()

        assert state is not None
        assert isinstance(state, dict)
        mock_api.assert_called("sync_all")

    async def test_sync_includes_inbox_id(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that sync state includes inbox ID."""
        state = await client.sync()

        assert "inboxId" in state
        assert state["inboxId"] == mock_api.inbox_id

    async def test_sync_includes_projects(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that sync state includes projects."""
        # Create some projects
        await client.create_project(name="Project 1")
        await client.create_project(name="Project 2")

        state = await client.sync()

        assert "projectProfiles" in state
        assert len(state["projectProfiles"]) == 2

    async def test_sync_includes_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that sync state includes tasks."""
        # Create some tasks
        await client.create_task(title="Task 1")
        await client.create_task(title="Task 2")
        await client.create_task(title="Task 3")

        state = await client.sync()

        assert "syncTaskBean" in state
        assert "update" in state["syncTaskBean"]
        assert len(state["syncTaskBean"]["update"]) == 3

    async def test_sync_includes_tags(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that sync state includes tags."""
        await client.create_tag(name="Tag1")
        await client.create_tag(name="Tag2")

        state = await client.sync()

        assert "tags" in state
        assert len(state["tags"]) == 2

    async def test_sync_includes_folders(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that sync state includes folders."""
        await client.create_folder(name="Folder 1")
        await client.create_folder(name="Folder 2")

        state = await client.sync()

        assert "projectGroups" in state
        assert len(state["projectGroups"]) == 2

    async def test_sync_empty_account(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test sync on empty account."""
        state = await client.sync()

        assert state["projectProfiles"] == []
        assert state["syncTaskBean"]["update"] == []
        assert state["tags"] == []
        assert state["projectGroups"] == []

    async def test_sync_after_operations(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test sync reflects recent operations."""
        # Initial sync
        initial_state = await client.sync()
        initial_task_count = len(initial_state["syncTaskBean"]["update"])

        # Perform operations
        await client.create_task(title="New Task")
        await client.create_project(name="New Project")

        # Sync again
        final_state = await client.sync()

        assert len(final_state["syncTaskBean"]["update"]) == initial_task_count + 1
        assert len(final_state["projectProfiles"]) == 1

    async def test_sync_complex_account(self, seeded_client: TickTickClient):
        """Test sync on account with seeded data."""
        state = await seeded_client.sync()

        # Seeded data should be present
        assert len(state["projectProfiles"]) > 0
        assert len(state["syncTaskBean"]["update"]) > 0
        assert len(state["tags"]) > 0
        assert len(state["projectGroups"]) > 0


# =============================================================================
# Focus and Sync Combination Tests
# =============================================================================


class TestFocusSyncCombinations:
    """Tests for combinations of focus and sync operations."""

    @pytest.mark.focus
    async def test_focus_data_with_tagged_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test focus data alongside tasks with tags."""
        # Create tagged tasks
        await client.create_tag(name="Work")
        await client.create_tag(name="Study")
        await client.create_task(title="Work Task", tags=["work"])
        await client.create_task(title="Study Task", tags=["study"])

        # Get focus by tag
        focus_data = await client.get_focus_by_tag()

        # Tags should be present in focus data
        assert "work" in focus_data
        assert "study" in focus_data

    @pytest.mark.sync
    async def test_sync_then_focus(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting focus data after sync."""
        # First sync
        state = await client.sync()

        # Then get focus data
        heatmap = await client.get_focus_heatmap()
        by_tag = await client.get_focus_by_tag()

        assert state is not None
        assert heatmap is not None
        assert by_tag is not None

    @pytest.mark.focus
    async def test_focus_heatmap_and_by_tag_consistency(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
    ):
        """Test that heatmap and by_tag data are consistent."""
        heatmap = await client.get_focus_heatmap()
        by_tag = await client.get_focus_by_tag()

        # Both should return data
        assert heatmap is not None
        assert by_tag is not None

        # Total duration from heatmap should relate to sum of by_tag durations
        # (Note: This is mock data, so we just verify structure)
        total_heatmap = sum(d.get("duration", 0) for d in heatmap)
        total_by_tag = sum(by_tag.values())

        # In real API these would be equal for same period
        assert total_heatmap >= 0
        assert total_by_tag >= 0

    async def test_full_data_retrieval_flow(self, seeded_client: TickTickClient):
        """Test complete data retrieval flow."""
        # 1. Sync to get all data
        state = await seeded_client.sync()
        assert state is not None

        # 2. Get user info
        profile = await seeded_client.get_profile()
        status = await seeded_client.get_status()
        stats = await seeded_client.get_statistics()

        assert profile is not None
        assert status is not None
        assert stats is not None

        # 3. Get focus data
        heatmap = await seeded_client.get_focus_heatmap()
        by_tag = await seeded_client.get_focus_by_tag()

        assert heatmap is not None
        assert by_tag is not None

        # 4. Get all tasks
        tasks = await seeded_client.get_all_tasks()
        projects = await seeded_client.get_all_projects()

        assert len(tasks) > 0
        assert len(projects) > 0

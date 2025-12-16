"""
Comprehensive User Operation Tests for TickTick Client.

This module tests all user-related functionality including:
- Get profile
- Get account status
- Get productivity statistics
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.conftest import MockUnifiedAPI
    from ticktick_mcp.client import TickTickClient


pytestmark = [pytest.mark.user, pytest.mark.unit]


# =============================================================================
# User Profile Tests
# =============================================================================


class TestUserProfile:
    """Tests for user profile retrieval."""

    async def test_get_profile(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting user profile."""
        profile = await client.get_profile()

        assert profile is not None
        assert profile.username is not None
        mock_api.assert_called("get_user_profile")

    async def test_get_profile_has_expected_fields(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that profile has all expected fields."""
        profile = await client.get_profile()

        assert hasattr(profile, "username")
        assert hasattr(profile, "display_name")
        assert hasattr(profile, "name")
        assert hasattr(profile, "email")
        assert hasattr(profile, "locale")
        assert hasattr(profile, "verified_email")

    async def test_get_profile_returns_configured_user(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that profile returns the configured mock user."""
        # Set specific user data
        mock_api.user.username = "custom@example.com"
        mock_api.user.display_name = "Custom User"
        mock_api.user.locale = "en_GB"

        profile = await client.get_profile()

        assert profile.username == "custom@example.com"
        assert profile.display_name == "Custom User"
        assert profile.locale == "en_GB"


# =============================================================================
# User Status Tests
# =============================================================================


class TestUserStatus:
    """Tests for user status retrieval."""

    async def test_get_status(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting user status."""
        status = await client.get_status()

        assert status is not None
        mock_api.assert_called("get_user_status")

    async def test_get_status_has_expected_fields(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that status has all expected fields."""
        status = await client.get_status()

        assert hasattr(status, "user_id")
        assert hasattr(status, "username")
        assert hasattr(status, "inbox_id")
        assert hasattr(status, "is_pro")
        assert hasattr(status, "team_user")

    async def test_get_status_pro_user(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting status for Pro user."""
        mock_api.user_status.is_pro = True
        mock_api.user_status.pro_end_date = "2026-12-31"

        status = await client.get_status()

        assert status.is_pro is True
        assert status.pro_end_date == "2026-12-31"

    async def test_get_status_free_user(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting status for free user."""
        mock_api.user_status.is_pro = False
        mock_api.user_status.pro_end_date = None

        status = await client.get_status()

        assert status.is_pro is False

    async def test_get_status_team_user(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting status for team user."""
        mock_api.user_status.team_user = True

        status = await client.get_status()

        assert status.team_user is True

    async def test_get_status_inbox_id(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that status includes inbox ID."""
        mock_api.user_status.inbox_id = "inbox999"

        status = await client.get_status()

        assert status.inbox_id == "inbox999"


# =============================================================================
# User Statistics Tests
# =============================================================================


class TestUserStatistics:
    """Tests for user statistics retrieval."""

    async def test_get_statistics(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting user statistics."""
        stats = await client.get_statistics()

        assert stats is not None
        mock_api.assert_called("get_user_statistics")

    async def test_get_statistics_has_expected_fields(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that statistics has all expected fields."""
        stats = await client.get_statistics()

        # Task completion stats
        assert hasattr(stats, "today_completed")
        assert hasattr(stats, "yesterday_completed")
        assert hasattr(stats, "total_completed")

        # Scoring
        assert hasattr(stats, "score")
        assert hasattr(stats, "level")

        # Pomodoro stats
        assert hasattr(stats, "today_pomo_count")
        assert hasattr(stats, "total_pomo_count")

    async def test_get_statistics_completion_data(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test statistics completion data."""
        mock_api.user_statistics.today_completed = 10
        mock_api.user_statistics.yesterday_completed = 8
        mock_api.user_statistics.total_completed = 1000

        stats = await client.get_statistics()

        assert stats.today_completed == 10
        assert stats.yesterday_completed == 8
        assert stats.total_completed == 1000

    async def test_get_statistics_scoring(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test statistics scoring data."""
        mock_api.user_statistics.score = 5000
        mock_api.user_statistics.level = 7

        stats = await client.get_statistics()

        assert stats.score == 5000
        assert stats.level == 7

    async def test_get_statistics_pomodoro_data(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test statistics pomodoro data."""
        mock_api.user_statistics.today_pomo_count = 5
        mock_api.user_statistics.yesterday_pomo_count = 8
        mock_api.user_statistics.total_pomo_count = 500
        mock_api.user_statistics.today_pomo_duration = 7500  # seconds
        mock_api.user_statistics.total_pomo_duration = 750000  # seconds

        stats = await client.get_statistics()

        assert stats.today_pomo_count == 5
        assert stats.yesterday_pomo_count == 8
        assert stats.total_pomo_count == 500

    async def test_get_statistics_computed_properties(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test computed properties on statistics."""
        mock_api.user_statistics.total_pomo_duration = 36000  # 10 hours in seconds

        stats = await client.get_statistics()

        # Should have computed hours property
        assert hasattr(stats, "total_pomo_duration_hours")
        assert stats.total_pomo_duration_hours == 10.0


# =============================================================================
# User Combination Tests
# =============================================================================


class TestUserCombinations:
    """Tests for combinations of user operations."""

    async def test_get_all_user_info(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting all user information in sequence."""
        profile = await client.get_profile()
        status = await client.get_status()
        stats = await client.get_statistics()

        assert profile is not None
        assert status is not None
        assert stats is not None

        # Verify all endpoints were called
        mock_api.assert_called("get_user_profile")
        mock_api.assert_called("get_user_status")
        mock_api.assert_called("get_user_statistics")

    async def test_profile_and_status_username_match(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that profile and status have consistent usernames."""
        mock_api.user.username = "test@example.com"
        mock_api.user_status.username = "test@example.com"

        profile = await client.get_profile()
        status = await client.get_status()

        assert profile.username == status.username

    async def test_user_info_with_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting user info alongside task operations."""
        # Create some tasks
        await client.create_task(title="Task 1")
        await client.create_task(title="Task 2")

        # Get user info
        profile = await client.get_profile()
        stats = await client.get_statistics()

        assert profile is not None
        assert stats is not None

        # Tasks should still exist
        tasks = await client.get_all_tasks()
        assert len(tasks) == 2

    async def test_statistics_reflects_activity(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that statistics data represents user activity."""
        # Configure mock to show active user
        mock_api.user_statistics.today_completed = 5
        mock_api.user_statistics.total_completed = 1000
        mock_api.user_statistics.level = 10
        mock_api.user_statistics.score = 10000

        stats = await client.get_statistics()

        # Active user should have reasonable stats
        assert stats.total_completed > 0
        assert stats.level >= 1
        assert stats.score > 0

    async def test_multiple_profile_calls_consistent(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that multiple profile calls return consistent data."""
        profile1 = await client.get_profile()
        profile2 = await client.get_profile()
        profile3 = await client.get_profile()

        assert profile1.username == profile2.username == profile3.username
        assert profile1.display_name == profile2.display_name == profile3.display_name

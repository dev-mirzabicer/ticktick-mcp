"""
API Router for TickTick Unified API.

This module provides the routing logic that decides which API version
to use for each operation. It handles:
- Primary API selection (usually V2 for richer features)
- Fallback logic when primary fails
- V1-only and V2-only operation routing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ticktick_mcp.api.v1 import TickTickV1Client
    from ticktick_mcp.api.v2 import TickTickV2Client

logger = logging.getLogger(__name__)


class APIPreference(StrEnum):
    """API preference for an operation."""

    V1_ONLY = auto()  # Only available in V1
    V2_ONLY = auto()  # Only available in V2
    V2_PRIMARY = auto()  # Prefer V2, fallback to V1
    V1_PRIMARY = auto()  # Prefer V1, fallback to V2


@dataclass
class OperationConfig:
    """Configuration for an operation."""

    preference: APIPreference
    description: str = ""


# Operation routing table
OPERATION_ROUTING: dict[str, OperationConfig] = {
    # Tasks
    "create_task": OperationConfig(
        APIPreference.V2_PRIMARY,
        "V2 supports tags, parent_id, and more fields",
    ),
    "get_task": OperationConfig(
        APIPreference.V2_PRIMARY,
        "V2 doesn't require project_id",
    ),
    "update_task": OperationConfig(
        APIPreference.V2_PRIMARY,
        "V2 has richer update options",
    ),
    "delete_task": OperationConfig(
        APIPreference.V2_PRIMARY,
        "V2 supports batch operations",
    ),
    "complete_task": OperationConfig(
        APIPreference.V1_PRIMARY,
        "V1 has dedicated endpoint, simpler",
    ),
    "list_all_tasks": OperationConfig(
        APIPreference.V2_ONLY,
        "V1 can only list per-project",
    ),
    "list_completed_tasks": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "list_deleted_tasks": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature (trash)",
    ),
    "move_task": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "set_task_parent": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature (subtasks)",
    ),
    # Projects
    "create_project": OperationConfig(
        APIPreference.V2_PRIMARY,
        "V2 supports more options",
    ),
    "get_project": OperationConfig(
        APIPreference.V1_PRIMARY,
        "V1 has dedicated endpoint",
    ),
    "get_project_with_data": OperationConfig(
        APIPreference.V1_ONLY,
        "V1-only feature (includes tasks + columns)",
    ),
    "update_project": OperationConfig(
        APIPreference.V2_PRIMARY,
        "V2 supports batch operations",
    ),
    "delete_project": OperationConfig(
        APIPreference.V2_PRIMARY,
        "V2 supports batch operations",
    ),
    "list_projects": OperationConfig(
        APIPreference.V2_PRIMARY,
        "V2 returns more metadata",
    ),
    # Project Groups
    "create_project_group": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "update_project_group": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "delete_project_group": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "list_project_groups": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    # Tags
    "create_tag": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "update_tag": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "rename_tag": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "delete_tag": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "merge_tags": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "list_tags": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    # User
    "get_user_profile": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "get_user_status": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "get_user_statistics": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "get_user_settings": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    # Focus/Pomodoro
    "get_focus_heatmap": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    "get_focus_by_tag": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    # Habits
    "get_habit_checkins": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
    # Sync
    "sync_all": OperationConfig(
        APIPreference.V2_ONLY,
        "V2-only feature",
    ),
}


@dataclass
class APIRouter:
    """
    Routes API operations to the appropriate client.

    This class manages both V1 and V2 clients and decides which
    to use for each operation based on the routing table.
    """

    v1_client: TickTickV1Client | None = None
    v2_client: TickTickV2Client | None = None

    # Cached state
    _v1_verified: bool = field(default=False, repr=False)
    _v2_verified: bool = field(default=False, repr=False)

    @property
    def has_v1(self) -> bool:
        """Check if V1 client is available and authenticated."""
        return self.v1_client is not None and self.v1_client.is_authenticated

    @property
    def has_v2(self) -> bool:
        """Check if V2 client is available and authenticated."""
        return self.v2_client is not None and self.v2_client.is_authenticated

    @property
    def is_fully_configured(self) -> bool:
        """Check if both APIs are available."""
        return self.has_v1 and self.has_v2

    def get_routing(self, operation: str) -> OperationConfig:
        """Get the routing configuration for an operation."""
        return OPERATION_ROUTING.get(
            operation,
            OperationConfig(APIPreference.V2_PRIMARY, "Default to V2"),
        )

    def can_execute(self, operation: str) -> bool:
        """Check if an operation can be executed with available clients."""
        config = self.get_routing(operation)

        if config.preference == APIPreference.V1_ONLY:
            return self.has_v1
        elif config.preference == APIPreference.V2_ONLY:
            return self.has_v2
        elif config.preference == APIPreference.V1_PRIMARY:
            return self.has_v1 or self.has_v2
        else:  # V2_PRIMARY
            return self.has_v2 or self.has_v1

    def get_primary_client(self, operation: str) -> tuple[str, object | None]:
        """
        Get the primary client for an operation.

        Returns:
            Tuple of (api_version, client) where api_version is 'v1' or 'v2'
        """
        config = self.get_routing(operation)

        if config.preference == APIPreference.V1_ONLY:
            return ("v1", self.v1_client)
        elif config.preference == APIPreference.V2_ONLY:
            return ("v2", self.v2_client)
        elif config.preference == APIPreference.V1_PRIMARY:
            if self.has_v1:
                return ("v1", self.v1_client)
            return ("v2", self.v2_client)
        else:  # V2_PRIMARY
            if self.has_v2:
                return ("v2", self.v2_client)
            return ("v1", self.v1_client)

    def get_fallback_client(self, operation: str) -> tuple[str, object | None]:
        """
        Get the fallback client for an operation.

        Returns:
            Tuple of (api_version, client) or (None, None) if no fallback
        """
        config = self.get_routing(operation)

        # V1_ONLY and V2_ONLY have no fallback
        if config.preference in (APIPreference.V1_ONLY, APIPreference.V2_ONLY):
            return (None, None)  # type: ignore

        if config.preference == APIPreference.V1_PRIMARY:
            if self.has_v2:
                return ("v2", self.v2_client)
        else:  # V2_PRIMARY
            if self.has_v1:
                return ("v1", self.v1_client)

        return (None, None)  # type: ignore

    async def verify_clients(self) -> dict[str, bool]:
        """
        Verify that both clients are working.

        Returns:
            Dict with 'v1' and 'v2' keys indicating verification status
        """
        results: dict[str, bool] = {"v1": False, "v2": False}

        if self.v1_client and self.v1_client.is_authenticated:
            try:
                results["v1"] = await self.v1_client.verify_authentication()
                self._v1_verified = results["v1"]
            except Exception as e:
                logger.warning("V1 verification failed: %s", e)
                self._v1_verified = False

        if self.v2_client and self.v2_client.is_authenticated:
            try:
                results["v2"] = await self.v2_client.verify_authentication()
                self._v2_verified = results["v2"]
            except Exception as e:
                logger.warning("V2 verification failed: %s", e)
                self._v2_verified = False

        return results

    def get_status(self) -> dict[str, any]:
        """Get the current status of the router."""
        return {
            "v1_available": self.has_v1,
            "v2_available": self.has_v2,
            "v1_verified": self._v1_verified,
            "v2_verified": self._v2_verified,
            "fully_configured": self.is_fully_configured,
        }

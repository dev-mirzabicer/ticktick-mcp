"""
TickTick SDK Constants and Enumerations.

This module defines all constants, enumerations, and type aliases
used throughout the TickTick SDK.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Literal
import os


# =============================================================================
# API Configuration
# =============================================================================
def _get_ticktick_domain():
    """Get the TickTick domain from environment or default."""
    domain = os.environ.get("TICKTICK_DOMAIN")
    return domain if domain else "ticktick.com"

# Base URLs
TICKTICK_API_BASE_V1 = f"https://api.{_get_ticktick_domain()}/open/v1"
TICKTICK_API_BASE_V2 = f"https://api.{_get_ticktick_domain()}/api/v2"
TICKTICK_OAUTH_BASE = f"https://{_get_ticktick_domain()}/oauth"

# Default timeout in seconds
DEFAULT_TIMEOUT = 30.0

# OAuth2 scopes
OAUTH_SCOPES = ["tasks:read", "tasks:write"]


# =============================================================================
# Task Enumerations
# =============================================================================


class TaskStatus(IntEnum):
    """Task completion status values."""

    ABANDONED = -1  # Won't do (V2 only)
    ACTIVE = 0  # Open/In progress
    COMPLETED_ALT = 1  # Completed (alternative, V2)
    COMPLETED = 2  # Completed (standard)

    @classmethod
    def is_completed(cls, status: int) -> bool:
        """Check if a status value indicates completion."""
        return status in (cls.COMPLETED, cls.COMPLETED_ALT)

    @classmethod
    def is_closed(cls, status: int) -> bool:
        """Check if a status value indicates the task is closed (completed or abandoned)."""
        return status in (cls.ABANDONED, cls.COMPLETED, cls.COMPLETED_ALT)


class TaskPriority(IntEnum):
    """Task priority levels."""

    NONE = 0
    LOW = 1
    MEDIUM = 3
    HIGH = 5

    @classmethod
    def from_string(cls, priority: str) -> TaskPriority:
        """Convert a string priority to TaskPriority."""
        mapping = {
            "none": cls.NONE,
            "low": cls.LOW,
            "medium": cls.MEDIUM,
            "high": cls.HIGH,
        }
        return mapping.get(priority.lower(), cls.NONE)

    def to_string(self) -> str:
        """Convert TaskPriority to a human-readable string."""
        return self.name.lower()


class TaskKind(StrEnum):
    """Task type/kind values."""

    TEXT = "TEXT"  # Standard task
    NOTE = "NOTE"  # Note
    CHECKLIST = "CHECKLIST"  # Checklist task


class RepeatFrom(IntEnum):
    """Recurrence calculation base."""

    DUE_DATE = 0  # Calculate next from due date
    COMPLETED_DATE = 1  # Calculate next from completion date
    UNKNOWN = 2


# =============================================================================
# Project Enumerations
# =============================================================================


class ProjectKind(StrEnum):
    """Project type values."""

    TASK = "TASK"
    NOTE = "NOTE"


class ViewMode(StrEnum):
    """Project view mode values."""

    LIST = "list"
    KANBAN = "kanban"
    TIMELINE = "timeline"


class Permission(StrEnum):
    """Project permission levels."""

    READ = "read"
    WRITE = "write"
    COMMENT = "comment"


# =============================================================================
# Sorting Enumerations
# =============================================================================


class SortOption(StrEnum):
    """Sorting options for tasks and lists."""

    SORT_ORDER = "sortOrder"  # Manual sort order
    DUE_DATE = "dueDate"
    TAG = "tag"
    PRIORITY = "priority"
    PROJECT = "project"
    TITLE = "title"
    NONE = "none"


# =============================================================================
# Subtask Status
# =============================================================================


class SubtaskStatus(IntEnum):
    """Subtask/checklist item status values."""

    NORMAL = 0
    COMPLETED = 1  # Note: Different from TaskStatus.COMPLETED which is 2


# =============================================================================
# Type Aliases
# =============================================================================

# Object ID types (24 hex characters for MongoDB-style IDs)
ObjectId = str
ETag = str  # 8-character lowercase alphanumeric version identifier
InboxId = str  # Format: inbox{user_id}

# Tag identifiers
TagLabel = str  # Display name (no special chars/whitespace)
TagName = str  # Lowercase identifier

# Time-related
TimeZoneName = str  # IANA timezone, e.g., "America/Los_Angeles"
ICalTrigger = str  # RFC 5545 reminder trigger format
RRule = str  # iCalendar RRULE + TickTick extensions

# Color format
HexColor = str  # Format: #rrggbb (lowercase, 7 chars)

# Date format literals
DateFormat = Literal["iso", "ticktick_v1", "ticktick_v2"]


# =============================================================================
# Date/Time Formats
# =============================================================================

# ISO 8601 with milliseconds (V2 task dates)
DATETIME_FORMAT_V2 = "%Y-%m-%dT%H:%M:%S.000+0000"

# ISO 8601 without milliseconds (V1)
DATETIME_FORMAT_V1 = "%Y-%m-%dT%H:%M:%S%z"

# Query parameter format for V2 closed tasks
DATETIME_FORMAT_V2_QUERY = "%Y-%m-%d %H:%M:%S"

# Date-only format for statistics
DATE_FORMAT_STATS = "%Y%m%d"


# =============================================================================
# HTTP Headers
# =============================================================================

# Simple User-Agent that works with V2 API (based on pyticktick)
V2_USER_AGENT = "Mozilla/5.0 (rv:145.0) Firefox/145.0"

# V2 X-Device version that works
V2_DEVICE_VERSION = 6430

# Legacy - kept for backwards compatibility but not recommended
# Use V2_USER_AGENT instead
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:95.0) "
    "Gecko/20100101 Firefox/95.0"
)

# Legacy - kept for backwards compatibility but not recommended
# Use minimal X-Device with only: platform, version, id
X_DEVICE_TEMPLATE = {
    "platform": "web",
    "os": "OS X",
    "device": "Firefox 95.0",
    "name": "",
    "version": 5303,
    "id": "",  # Will be set dynamically
    "channel": "website",
    "campaign": "",
    "websocket": "",
}


# =============================================================================
# API Version Enum
# =============================================================================


class APIVersion(StrEnum):
    """API version identifiers."""

    V1 = "v1"
    V2 = "v2"

    @property
    def base_url(self) -> str:
        """Get the base URL for this API version."""
        if self == APIVersion.V1:
            return TICKTICK_API_BASE_V1
        return TICKTICK_API_BASE_V2

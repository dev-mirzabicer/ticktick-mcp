"""
TickTick V2 API Client (Unofficial/Reverse-Engineered).

This module provides the client for TickTick's unofficial V2 API,
which uses session-based authentication and provides significantly
more functionality than V1.

Features:
    - Session-based authentication (username/password)
    - Batch operations (tasks, projects, tags)
    - Tags management
    - Project groups/folders
    - User profile and statistics
    - Focus/Pomodoro tracking
    - Habits
    - Full state sync
"""

from ticktick_mcp.api.v2.client import TickTickV2Client
from ticktick_mcp.api.v2.auth import SessionHandler

__all__ = ["TickTickV2Client", "SessionHandler"]

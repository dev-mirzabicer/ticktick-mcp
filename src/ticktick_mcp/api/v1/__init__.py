"""
TickTick V1 API Client (Official OpenAPI).

This module provides the client for TickTick's official V1 Open API,
which uses OAuth2 for authentication.

Features:
    - OAuth2 authentication flow
    - Task CRUD operations
    - Project CRUD operations
    - Get project with data (tasks + columns)
"""

from ticktick_mcp.api.v1.client import TickTickV1Client
from ticktick_mcp.api.v1.auth import OAuth2Handler

__all__ = ["TickTickV1Client", "OAuth2Handler"]

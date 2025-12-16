"""
TickTick API Modules.

This package contains the V1 and V2 API client implementations.

Modules:
    v1: Official TickTick Open API (OAuth2)
    v2: Unofficial TickTick API (Session-based)
"""

from ticktick_mcp.api.v1 import TickTickV1Client
from ticktick_mcp.api.v2 import TickTickV2Client

__all__ = ["TickTickV1Client", "TickTickV2Client"]

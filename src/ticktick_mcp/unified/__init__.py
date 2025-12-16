"""
TickTick Unified API Layer.

This package provides the version-agnostic abstraction layer that
intelligently routes operations between V1 and V2 APIs.

The Unified API:
- Manages both V1 and V2 client instances
- Routes operations to the appropriate API
- Converts between unified models and API-specific formats
- Handles fallbacks when one API fails
- Ensures both APIs are authenticated and functional

Architecture:
    ┌─────────────────────────────────────────┐
    │           UnifiedTickTickAPI            │
    │  ─────────────────────────────────────  │
    │  • Single entry point for all ops       │
    │  • Version-agnostic methods             │
    │  • Unified model input/output           │
    └─────────────────────────────────────────┘
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
    ┌───────────────┐     ┌───────────────┐
    │ TaskService   │     │ ProjectService│
    │ TagService    │     │ UserService   │
    │ FocusService  │     │ ...           │
    └───────────────┘     └───────────────┘
            │                     │
            └──────────┬──────────┘
                       ▼
    ┌─────────────────────────────────────────┐
    │          APIRouter                       │
    │  ─────────────────────────────────────  │
    │  • Decides V1 vs V2 for each operation  │
    │  • Handles conversion & fallbacks       │
    └─────────────────────────────────────────┘
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
        V1Client              V2Client
"""

from ticktick_mcp.unified.api import UnifiedTickTickAPI
from ticktick_mcp.unified.router import APIRouter

__all__ = ["UnifiedTickTickAPI", "APIRouter"]

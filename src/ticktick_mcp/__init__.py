"""
TickTick MCP Server - Enterprise-grade MCP server with unified V1/V2 API support.

This package provides a comprehensive Model Context Protocol (MCP) server
for TickTick, combining both the official V1 API and the unofficial V2 API
to provide maximum functionality.

Architecture:
    MCP Tools Layer
         │
         ▼
    TickTick Client (version-agnostic)
         │
         ▼
    Unified API Layer (routing & normalization)
         │
    ┌────┴────┐
    ▼         ▼
  V1 API    V2 API
  Module    Module
"""

__version__ = "0.1.0"
__author__ = "TickTick MCP Contributors"

from ticktick_mcp.exceptions import (
    TickTickError,
    TickTickAuthenticationError,
    TickTickAPIError,
    TickTickValidationError,
    TickTickRateLimitError,
    TickTickNotFoundError,
)

__all__ = [
    "__version__",
    "TickTickError",
    "TickTickAuthenticationError",
    "TickTickAPIError",
    "TickTickValidationError",
    "TickTickRateLimitError",
    "TickTickNotFoundError",
]

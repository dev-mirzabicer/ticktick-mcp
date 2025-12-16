"""
Unified Tag Model.

This module provides the canonical Tag model.
Tags are a V2-only feature.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import Field

from ticktick_mcp.models.base import TickTickModel
from ticktick_mcp.models.project import SortOption


class Tag(TickTickModel):
    """
    Tag model.

    Tags are a V2-only feature for organizing tasks.
    """

    # Identifiers
    name: str  # Lowercase identifier
    label: str  # Display name
    raw_name: str | None = Field(default=None, alias="rawName")
    etag: str | None = None

    # Appearance
    color: str | None = None

    # Hierarchy
    parent: str | None = None

    # Sorting
    sort_option: SortOption | None = Field(default=None, alias="sortOption")
    sort_type: str | None = Field(default=None, alias="sortType")
    sort_order: int | None = Field(default=None, alias="sortOrder")

    # Other
    type: int | None = None

    @property
    def is_nested(self) -> bool:
        """Check if this tag is nested under another tag."""
        return self.parent is not None

    @classmethod
    def create(
        cls,
        label: str,
        color: str | None = None,
        parent: str | None = None,
    ) -> Self:
        """Create a new tag with auto-generated name."""
        name = label.lower().replace(" ", "")
        return cls(
            name=name,
            label=label,
            color=color,
            parent=parent,
        )

    @classmethod
    def from_v2(cls, data: dict[str, Any]) -> Self:
        """Create from V2 API response."""
        return cls.model_validate(data)

    def to_v2_create_dict(self) -> dict[str, Any]:
        """Convert to V2 API create format."""
        data: dict[str, Any] = {
            "label": self.label,
            "name": self.name,
        }

        if self.color is not None:
            data["color"] = self.color
        if self.parent is not None:
            data["parent"] = self.parent
        if self.sort_type is not None:
            data["sortType"] = self.sort_type
        if self.sort_order is not None:
            data["sortOrder"] = self.sort_order

        return data

    def to_v2_update_dict(self) -> dict[str, Any]:
        """Convert to V2 API update format."""
        data: dict[str, Any] = {
            "name": self.name,
            "label": self.label,
            "rawName": self.name,
        }

        if self.color is not None:
            data["color"] = self.color
        if self.parent is not None:
            data["parent"] = self.parent
        if self.sort_type is not None:
            data["sortType"] = self.sort_type
        if self.sort_order is not None:
            data["sortOrder"] = self.sort_order

        return data

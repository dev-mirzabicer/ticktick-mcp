"""
Unified User Models.

This module provides models for user profile, status, and statistics.
These are V2-only features.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import Field

from ticktick_mcp.models.base import TickTickModel


class UserStatus(TickTickModel):
    """User subscription and account status."""

    user_id: str = Field(alias="userId")
    user_code: str | None = Field(default=None, alias="userCode")
    username: str
    inbox_id: str = Field(alias="inboxId")

    # Subscription
    is_pro: bool = Field(default=False, alias="pro")
    pro_start_date: str | None = Field(default=None, alias="proStartDate")
    pro_end_date: str | None = Field(default=None, alias="proEndDate")
    subscribe_type: str | None = Field(default=None, alias="subscribeType")
    subscribe_freq: str | None = Field(default=None, alias="subscribeFreq")
    need_subscribe: bool = Field(default=False, alias="needSubscribe")
    free_trial: bool = Field(default=False, alias="freeTrial")
    grace_period: bool = Field(default=False, alias="gracePeriod")

    # Team
    team_user: bool = Field(default=False, alias="teamUser")
    team_pro: bool = Field(default=False, alias="teamPro")
    active_team_user: bool = Field(default=False, alias="activeTeamUser")

    @classmethod
    def from_v2(cls, data: dict[str, Any]) -> Self:
        """Create from V2 API response."""
        return cls.model_validate(data)


class User(TickTickModel):
    """User profile information."""

    username: str
    display_name: str | None = Field(default=None, alias="displayName")
    name: str | None = None
    picture: str | None = None
    locale: str | None = None
    site_domain: str | None = Field(default=None, alias="siteDomain")
    user_code: str | None = Field(default=None, alias="userCode")
    verified_email: bool = Field(default=False, alias="verifiedEmail")
    filled_password: bool = Field(default=False, alias="filledPassword")
    email: str | None = None

    @classmethod
    def from_v2(cls, data: dict[str, Any]) -> Self:
        """Create from V2 API response."""
        return cls.model_validate(data)


class TaskCount(TickTickModel):
    """Task completion counts."""

    complete_count: int = Field(default=0, alias="completeCount")
    not_complete_count: int = Field(default=0, alias="notCompleteCount")

    @property
    def total(self) -> int:
        """Get total task count."""
        return self.complete_count + self.not_complete_count


class UserStatistics(TickTickModel):
    """User productivity statistics."""

    # Score and level
    score: int = 0
    level: int = 0

    # Task completion
    yesterday_completed: int = Field(default=0, alias="yesterdayCompleted")
    today_completed: int = Field(default=0, alias="todayCompleted")
    total_completed: int = Field(default=0, alias="totalCompleted")

    # Score history (date -> score)
    score_by_day: dict[str, int] = Field(default_factory=dict, alias="scoreByDay")

    # Task history (date -> counts)
    task_by_day: dict[str, TaskCount] = Field(default_factory=dict, alias="taskByDay")
    task_by_week: dict[str, TaskCount] = Field(default_factory=dict, alias="taskByWeek")
    task_by_month: dict[str, TaskCount] = Field(default_factory=dict, alias="taskByMonth")

    # Pomodoro stats
    today_pomo_count: int = Field(default=0, alias="todayPomoCount")
    yesterday_pomo_count: int = Field(default=0, alias="yesterdayPomoCount")
    total_pomo_count: int = Field(default=0, alias="totalPomoCount")
    today_pomo_duration: int = Field(default=0, alias="todayPomoDuration")
    yesterday_pomo_duration: int = Field(default=0, alias="yesterdayPomoDuration")
    total_pomo_duration: int = Field(default=0, alias="totalPomoDuration")
    pomo_goal: int = Field(default=0, alias="pomoGoal")
    pomo_duration_goal: int = Field(default=0, alias="pomoDurationGoal")

    # Pomodoro history
    pomo_by_day: dict[str, Any] = Field(default_factory=dict, alias="pomoByDay")
    pomo_by_week: dict[str, Any] = Field(default_factory=dict, alias="pomoByWeek")
    pomo_by_month: dict[str, Any] = Field(default_factory=dict, alias="pomoByMonth")

    @classmethod
    def from_v2(cls, data: dict[str, Any]) -> Self:
        """Create from V2 API response."""
        # Parse task count dicts
        if "taskByDay" in data:
            data["taskByDay"] = {
                k: TaskCount.model_validate(v) if isinstance(v, dict) else v
                for k, v in data["taskByDay"].items()
            }
        if "taskByWeek" in data:
            data["taskByWeek"] = {
                k: TaskCount.model_validate(v) if isinstance(v, dict) else v
                for k, v in data["taskByWeek"].items()
            }
        if "taskByMonth" in data:
            data["taskByMonth"] = {
                k: TaskCount.model_validate(v) if isinstance(v, dict) else v
                for k, v in data["taskByMonth"].items()
            }
        return cls.model_validate(data)

    @property
    def total_pomo_duration_hours(self) -> float:
        """Get total pomodoro duration in hours."""
        return self.total_pomo_duration / 3600 if self.total_pomo_duration else 0

    @property
    def today_pomo_duration_minutes(self) -> float:
        """Get today's pomodoro duration in minutes."""
        return self.today_pomo_duration / 60 if self.today_pomo_duration else 0

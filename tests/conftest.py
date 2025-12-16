"""
Pytest Configuration and Fixtures for TickTick Client Tests.

This module provides comprehensive fixtures, mock factories, and shared
utilities for testing the TickTick Client.

Architecture:
    - MockUnifiedAPI: Async mock for UnifiedTickTickAPI
    - Factories: Generate test data (tasks, projects, tags, etc.)
    - Fixtures: Provide configured clients and mock data
    - Markers: Custom pytest markers for test categorization
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ticktick_mcp.client import TickTickClient
from ticktick_mcp.models import (
    Task,
    ChecklistItem,
    Project,
    ProjectGroup,
    ProjectData,
    Column,
    Tag,
    User,
    UserStatus,
    UserStatistics,
)
from ticktick_mcp.constants import TaskStatus, TaskPriority, ProjectKind, ViewMode


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "tasks: Task-related tests")
    config.addinivalue_line("markers", "projects: Project-related tests")
    config.addinivalue_line("markers", "tags: Tag-related tests")
    config.addinivalue_line("markers", "user: User-related tests")
    config.addinivalue_line("markers", "focus: Focus/Pomodoro tests")
    config.addinivalue_line("markers", "sync: Sync-related tests")
    config.addinivalue_line("markers", "errors: Error handling tests")
    config.addinivalue_line("markers", "lifecycle: Client lifecycle tests")


# =============================================================================
# Time Utilities
# =============================================================================


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


def days_ago(n: int) -> datetime:
    """Get datetime n days ago."""
    return utc_now() - timedelta(days=n)


def days_from_now(n: int) -> datetime:
    """Get datetime n days from now."""
    return utc_now() + timedelta(days=n)


# =============================================================================
# ID Generators
# =============================================================================


class IDGenerator:
    """Thread-safe ID generator for test objects."""

    _counter: int = 0

    @classmethod
    def reset(cls) -> None:
        """Reset counter (call in fixtures)."""
        cls._counter = 0

    @classmethod
    def next_id(cls, prefix: str = "") -> str:
        """Generate next unique ID."""
        cls._counter += 1
        hex_part = f"{cls._counter:024x}"
        return f"{prefix}{hex_part}" if prefix else hex_part

    @classmethod
    def task_id(cls) -> str:
        """Generate task ID."""
        return cls.next_id()

    @classmethod
    def project_id(cls) -> str:
        """Generate project ID."""
        return cls.next_id()

    @classmethod
    def folder_id(cls) -> str:
        """Generate folder/project group ID."""
        return cls.next_id()

    @classmethod
    def inbox_id(cls) -> str:
        """Generate inbox ID."""
        cls._counter += 1
        return f"inbox{cls._counter}"


# =============================================================================
# Test Data Factories
# =============================================================================


class TaskFactory:
    """Factory for creating Task test objects."""

    @staticmethod
    def create(
        id: str | None = None,
        project_id: str | None = None,
        title: str = "Test Task",
        content: str | None = None,
        status: int = TaskStatus.ACTIVE,
        priority: int = TaskPriority.NONE,
        start_date: datetime | None = None,
        due_date: datetime | None = None,
        completed_time: datetime | None = None,
        tags: list[str] | None = None,
        items: list[ChecklistItem] | None = None,
        parent_id: str | None = None,
        child_ids: list[str] | None = None,
        time_zone: str = "America/Los_Angeles",
        is_all_day: bool = False,
        repeat_flag: str | None = None,
        **kwargs,
    ) -> Task:
        """Create a Task with sensible defaults."""
        return Task(
            id=id or IDGenerator.task_id(),
            project_id=project_id or IDGenerator.project_id(),
            title=title,
            content=content,
            status=status,
            priority=priority,
            start_date=start_date,
            due_date=due_date,
            completed_time=completed_time,
            tags=tags or [],
            items=items or [],
            parent_id=parent_id,
            child_ids=child_ids or [],
            time_zone=time_zone,
            is_all_day=is_all_day,
            repeat_flag=repeat_flag,
            created_time=utc_now(),
            modified_time=utc_now(),
            sort_order=0,
            **kwargs,
        )

    @staticmethod
    def create_with_due_date(days_offset: int = 1, **kwargs) -> Task:
        """Create task with due date relative to today."""
        due = days_from_now(days_offset) if days_offset >= 0 else days_ago(-days_offset)
        return TaskFactory.create(due_date=due, **kwargs)

    @staticmethod
    def create_completed(**kwargs) -> Task:
        """Create a completed task."""
        return TaskFactory.create(
            status=TaskStatus.COMPLETED,
            completed_time=utc_now(),
            **kwargs,
        )

    @staticmethod
    def create_overdue(**kwargs) -> Task:
        """Create an overdue task."""
        return TaskFactory.create(
            due_date=days_ago(3),
            status=TaskStatus.ACTIVE,
            **kwargs,
        )

    @staticmethod
    def create_with_subtasks(subtask_count: int = 3, **kwargs) -> Task:
        """Create task with checklist items."""
        items = [
            ChecklistItem(
                id=IDGenerator.task_id(),
                title=f"Subtask {i+1}",
                status=0,
                sort_order=i,
            )
            for i in range(subtask_count)
        ]
        return TaskFactory.create(items=items, **kwargs)

    @staticmethod
    def create_with_tags(tags: list[str], **kwargs) -> Task:
        """Create task with specified tags."""
        return TaskFactory.create(tags=tags, **kwargs)

    @staticmethod
    def create_recurring(rrule: str = "RRULE:FREQ=DAILY;INTERVAL=1", **kwargs) -> Task:
        """Create recurring task."""
        return TaskFactory.create(repeat_flag=rrule, **kwargs)

    @staticmethod
    def create_child_task(parent_id: str, **kwargs) -> Task:
        """Create a child task (subtask)."""
        return TaskFactory.create(parent_id=parent_id, **kwargs)

    @staticmethod
    def create_batch(count: int, **kwargs) -> list[Task]:
        """Create multiple tasks."""
        return [TaskFactory.create(title=f"Task {i+1}", **kwargs) for i in range(count)]

    @staticmethod
    def create_priority_set() -> list[Task]:
        """Create one task of each priority level."""
        return [
            TaskFactory.create(title="No Priority", priority=TaskPriority.NONE),
            TaskFactory.create(title="Low Priority", priority=TaskPriority.LOW),
            TaskFactory.create(title="Medium Priority", priority=TaskPriority.MEDIUM),
            TaskFactory.create(title="High Priority", priority=TaskPriority.HIGH),
        ]


class ProjectFactory:
    """Factory for creating Project test objects."""

    @staticmethod
    def create(
        id: str | None = None,
        name: str = "Test Project",
        color: str | None = "#F18181",
        kind: str = ProjectKind.TASK,
        view_mode: str = ViewMode.LIST,
        group_id: str | None = None,
        closed: bool = False,
        sort_order: int = 0,
        **kwargs,
    ) -> Project:
        """Create a Project with sensible defaults."""
        return Project(
            id=id or IDGenerator.project_id(),
            name=name,
            color=color,
            kind=kind,
            view_mode=view_mode,
            group_id=group_id,
            closed=closed,
            sort_order=sort_order,
            **kwargs,
        )

    @staticmethod
    def create_inbox(user_id: int = 123456789) -> Project:
        """Create an inbox project."""
        return ProjectFactory.create(
            id=f"inbox{user_id}",
            name="Inbox",
            color=None,
        )

    @staticmethod
    def create_note_project(**kwargs) -> Project:
        """Create a NOTE type project."""
        return ProjectFactory.create(kind=ProjectKind.NOTE, **kwargs)

    @staticmethod
    def create_kanban_project(**kwargs) -> Project:
        """Create a kanban view project."""
        return ProjectFactory.create(view_mode=ViewMode.KANBAN, **kwargs)

    @staticmethod
    def create_in_folder(folder_id: str, **kwargs) -> Project:
        """Create project in a folder."""
        return ProjectFactory.create(group_id=folder_id, **kwargs)

    @staticmethod
    def create_batch(count: int, **kwargs) -> list[Project]:
        """Create multiple projects."""
        return [ProjectFactory.create(name=f"Project {i+1}", **kwargs) for i in range(count)]


class FolderFactory:
    """Factory for creating ProjectGroup (folder) test objects."""

    @staticmethod
    def create(
        id: str | None = None,
        name: str = "Test Folder",
        sort_order: int = 0,
        **kwargs,
    ) -> ProjectGroup:
        """Create a ProjectGroup with sensible defaults."""
        return ProjectGroup(
            id=id or IDGenerator.folder_id(),
            name=name,
            sort_order=sort_order,
            **kwargs,
        )

    @staticmethod
    def create_batch(count: int, **kwargs) -> list[ProjectGroup]:
        """Create multiple folders."""
        return [FolderFactory.create(name=f"Folder {i+1}", **kwargs) for i in range(count)]


class TagFactory:
    """Factory for creating Tag test objects."""

    @staticmethod
    def create(
        name: str | None = None,
        label: str = "TestTag",
        color: str | None = "#86BB6D",
        parent: str | None = None,
        sort_order: int = 0,
        **kwargs,
    ) -> Tag:
        """Create a Tag with sensible defaults."""
        tag_name = name or label.lower().replace(" ", "")
        return Tag(
            name=tag_name,
            label=label,
            color=color,
            parent=parent,
            sort_order=sort_order,
            **kwargs,
        )

    @staticmethod
    def create_nested(parent_label: str, child_labels: list[str]) -> list[Tag]:
        """Create a parent tag with children."""
        parent = TagFactory.create(label=parent_label)
        children = [
            TagFactory.create(label=label, parent=parent.name)
            for label in child_labels
        ]
        return [parent] + children

    @staticmethod
    def create_batch(labels: list[str]) -> list[Tag]:
        """Create multiple tags from labels."""
        return [TagFactory.create(label=label) for label in labels]


class UserFactory:
    """Factory for creating User test objects."""

    @staticmethod
    def create(
        username: str = "testuser@example.com",
        display_name: str = "Test User",
        name: str = "Test",
        email: str | None = None,
        locale: str = "en_US",
        verified_email: bool = True,
        **kwargs,
    ) -> User:
        """Create a User with sensible defaults."""
        return User(
            username=username,
            display_name=display_name,
            name=name,
            email=email or username,
            locale=locale,
            verified_email=verified_email,
            **kwargs,
        )


class UserStatusFactory:
    """Factory for creating UserStatus test objects."""

    @staticmethod
    def create(
        user_id: str = "123456789",
        username: str = "testuser@example.com",
        inbox_id: str = "inbox123456789",
        is_pro: bool = True,
        team_user: bool = False,
        pro_end_date: str | None = None,
        **kwargs,
    ) -> UserStatus:
        """Create a UserStatus with sensible defaults."""
        return UserStatus(
            user_id=user_id,
            username=username,
            inbox_id=inbox_id,
            is_pro=is_pro,
            team_user=team_user,
            pro_end_date=pro_end_date or "2026-12-31",
            **kwargs,
        )

    @staticmethod
    def create_free_user(**kwargs) -> UserStatus:
        """Create a free tier user status."""
        return UserStatusFactory.create(is_pro=False, pro_end_date=None, **kwargs)


class UserStatisticsFactory:
    """Factory for creating UserStatistics test objects."""

    @staticmethod
    def create(
        score: int = 1000,
        level: int = 5,
        today_completed: int = 3,
        yesterday_completed: int = 5,
        total_completed: int = 500,
        today_pomo_count: int = 2,
        yesterday_pomo_count: int = 4,
        total_pomo_count: int = 100,
        today_pomo_duration: int = 3000,
        yesterday_pomo_duration: int = 6000,
        total_pomo_duration: int = 150000,
        **kwargs,
    ) -> UserStatistics:
        """Create UserStatistics with sensible defaults."""
        return UserStatistics(
            score=score,
            level=level,
            today_completed=today_completed,
            yesterday_completed=yesterday_completed,
            total_completed=total_completed,
            today_pomo_count=today_pomo_count,
            yesterday_pomo_count=yesterday_pomo_count,
            total_pomo_count=total_pomo_count,
            today_pomo_duration=today_pomo_duration,
            yesterday_pomo_duration=yesterday_pomo_duration,
            total_pomo_duration=total_pomo_duration,
            **kwargs,
        )


class ProjectDataFactory:
    """Factory for creating ProjectData test objects."""

    @staticmethod
    def create(
        project: Project | None = None,
        tasks: list[Task] | None = None,
        columns: list[Column] | None = None,
    ) -> ProjectData:
        """Create ProjectData with sensible defaults."""
        proj = project or ProjectFactory.create()
        return ProjectData(
            project=proj,
            tasks=tasks or TaskFactory.create_batch(3, project_id=proj.id),
            columns=columns or [],
        )


class ColumnFactory:
    """Factory for creating Column test objects."""

    @staticmethod
    def create(
        id: str | None = None,
        project_id: str | None = None,
        name: str = "To Do",
        sort_order: int = 0,
    ) -> Column:
        """Create a Column with sensible defaults."""
        return Column(
            id=id or IDGenerator.next_id(),
            project_id=project_id or IDGenerator.project_id(),
            name=name,
            sort_order=sort_order,
        )

    @staticmethod
    def create_kanban_set(project_id: str) -> list[Column]:
        """Create a standard kanban column set."""
        return [
            ColumnFactory.create(project_id=project_id, name="To Do", sort_order=0),
            ColumnFactory.create(project_id=project_id, name="In Progress", sort_order=1),
            ColumnFactory.create(project_id=project_id, name="Done", sort_order=2),
        ]


# =============================================================================
# Mock API Classes
# =============================================================================


class MockUnifiedAPI:
    """
    Comprehensive mock for UnifiedTickTickAPI.

    This mock provides configurable behavior for all API operations,
    allowing tests to simulate various scenarios including success,
    failure, and edge cases.
    """

    def __init__(self):
        """Initialize mock with default data stores."""
        self.tasks: dict[str, Task] = {}
        self.projects: dict[str, Project] = {}
        self.folders: dict[str, ProjectGroup] = {}
        self.tags: dict[str, Tag] = {}
        self.user: User = UserFactory.create()
        self.user_status: UserStatus = UserStatusFactory.create()
        self.user_statistics: UserStatistics = UserStatisticsFactory.create()
        self.inbox_id: str = "inbox123456789"
        self._initialized: bool = False

        # Track method calls for verification
        self.call_history: list[tuple[str, tuple, dict]] = []

        # Configurable behaviors
        self.should_fail: dict[str, Exception | None] = {}
        self.delays: dict[str, float] = {}

    def _record_call(self, method: str, args: tuple, kwargs: dict) -> None:
        """Record method call for verification."""
        self.call_history.append((method, args, kwargs))

    def _check_failure(self, method: str) -> None:
        """Check if method should raise an exception."""
        if method in self.should_fail and self.should_fail[method]:
            raise self.should_fail[method]

    async def initialize(self) -> None:
        """Mock initialization."""
        self._record_call("initialize", (), {})
        self._check_failure("initialize")
        self._initialized = True

    async def close(self) -> None:
        """Mock close."""
        self._record_call("close", (), {})
        self._initialized = False

    # -------------------------------------------------------------------------
    # Task Operations
    # -------------------------------------------------------------------------

    async def create_task(
        self,
        title: str,
        project_id: str | None = None,
        **kwargs,
    ) -> Task:
        """Mock task creation."""
        self._record_call("create_task", (title,), {"project_id": project_id, **kwargs})
        self._check_failure("create_task")

        task = TaskFactory.create(
            title=title,
            project_id=project_id or self.inbox_id,
            **kwargs,
        )
        self.tasks[task.id] = task
        return task

    async def get_task(self, task_id: str, project_id: str | None = None) -> Task:
        """Mock get task."""
        self._record_call("get_task", (task_id,), {"project_id": project_id})
        self._check_failure("get_task")

        if task_id not in self.tasks:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Task not found: {task_id}")
        return self.tasks[task_id]

    async def update_task(self, task: Task) -> Task:
        """Mock update task."""
        self._record_call("update_task", (task,), {})
        self._check_failure("update_task")

        if task.id not in self.tasks:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Task not found: {task.id}")

        task.modified_time = utc_now()
        self.tasks[task.id] = task
        return task

    async def complete_task(self, task_id: str, project_id: str) -> None:
        """Mock complete task."""
        self._record_call("complete_task", (task_id, project_id), {})
        self._check_failure("complete_task")

        if task_id not in self.tasks:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Task not found: {task_id}")

        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_time = utc_now()

    async def delete_task(self, task_id: str, project_id: str) -> None:
        """Mock delete task."""
        self._record_call("delete_task", (task_id, project_id), {})
        self._check_failure("delete_task")

        if task_id not in self.tasks:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Task not found: {task_id}")

        del self.tasks[task_id]

    async def list_all_tasks(self) -> list[Task]:
        """Mock list all tasks."""
        self._record_call("list_all_tasks", (), {})
        self._check_failure("list_all_tasks")

        return [t for t in self.tasks.values() if t.status == TaskStatus.ACTIVE]

    async def list_completed_tasks(
        self,
        from_date: datetime,
        to_date: datetime,
        limit: int = 100,
    ) -> list[Task]:
        """Mock list completed tasks."""
        self._record_call("list_completed_tasks", (from_date, to_date), {"limit": limit})
        self._check_failure("list_completed_tasks")

        completed = [
            t for t in self.tasks.values()
            if t.status == TaskStatus.COMPLETED
            and t.completed_time
            and from_date <= t.completed_time <= to_date
        ]
        return completed[:limit]

    async def move_task(
        self,
        task_id: str,
        from_project_id: str,
        to_project_id: str,
    ) -> None:
        """Mock move task."""
        self._record_call("move_task", (task_id, from_project_id, to_project_id), {})
        self._check_failure("move_task")

        if task_id not in self.tasks:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Task not found: {task_id}")

        self.tasks[task_id].project_id = to_project_id

    async def set_task_parent(
        self,
        task_id: str,
        project_id: str,
        parent_id: str,
    ) -> None:
        """Mock set task parent."""
        self._record_call("set_task_parent", (task_id, project_id, parent_id), {})
        self._check_failure("set_task_parent")

        if task_id not in self.tasks:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Task not found: {task_id}")

        self.tasks[task_id].parent_id = parent_id

        if parent_id in self.tasks:
            parent = self.tasks[parent_id]
            if task_id not in parent.child_ids:
                parent.child_ids.append(task_id)

    # -------------------------------------------------------------------------
    # Project Operations
    # -------------------------------------------------------------------------

    async def list_projects(self) -> list[Project]:
        """Mock list projects."""
        self._record_call("list_projects", (), {})
        self._check_failure("list_projects")
        return list(self.projects.values())

    async def get_project(self, project_id: str) -> Project:
        """Mock get project."""
        self._record_call("get_project", (project_id,), {})
        self._check_failure("get_project")

        if project_id not in self.projects:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Project not found: {project_id}")
        return self.projects[project_id]

    async def get_project_with_data(self, project_id: str) -> ProjectData:
        """Mock get project with data."""
        self._record_call("get_project_with_data", (project_id,), {})
        self._check_failure("get_project_with_data")

        if project_id not in self.projects:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Project not found: {project_id}")

        project = self.projects[project_id]
        tasks = [t for t in self.tasks.values() if t.project_id == project_id]
        return ProjectData(project=project, tasks=tasks, columns=[])

    async def create_project(
        self,
        name: str,
        color: str | None = None,
        kind: str = "TASK",
        view_mode: str = "list",
        group_id: str | None = None,
    ) -> Project:
        """Mock create project."""
        self._record_call("create_project", (name,), {
            "color": color, "kind": kind, "view_mode": view_mode, "group_id": group_id
        })
        self._check_failure("create_project")

        project = ProjectFactory.create(
            name=name,
            color=color,
            kind=kind,
            view_mode=view_mode,
            group_id=group_id,
        )
        self.projects[project.id] = project
        return project

    async def delete_project(self, project_id: str) -> None:
        """Mock delete project."""
        self._record_call("delete_project", (project_id,), {})
        self._check_failure("delete_project")

        if project_id not in self.projects:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Project not found: {project_id}")

        del self.projects[project_id]
        # Also delete associated tasks
        self.tasks = {k: v for k, v in self.tasks.items() if v.project_id != project_id}

    # -------------------------------------------------------------------------
    # Folder Operations
    # -------------------------------------------------------------------------

    async def list_project_groups(self) -> list[ProjectGroup]:
        """Mock list project groups (folders)."""
        self._record_call("list_project_groups", (), {})
        self._check_failure("list_project_groups")
        return list(self.folders.values())

    async def create_project_group(self, name: str) -> ProjectGroup:
        """Mock create project group."""
        self._record_call("create_project_group", (name,), {})
        self._check_failure("create_project_group")

        folder = FolderFactory.create(name=name)
        self.folders[folder.id] = folder
        return folder

    async def delete_project_group(self, group_id: str) -> None:
        """Mock delete project group."""
        self._record_call("delete_project_group", (group_id,), {})
        self._check_failure("delete_project_group")

        if group_id not in self.folders:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Folder not found: {group_id}")

        del self.folders[group_id]
        # Ungroup projects in this folder
        for project in self.projects.values():
            if project.group_id == group_id:
                project.group_id = None

    # -------------------------------------------------------------------------
    # Tag Operations
    # -------------------------------------------------------------------------

    async def list_tags(self) -> list[Tag]:
        """Mock list tags."""
        self._record_call("list_tags", (), {})
        self._check_failure("list_tags")
        return list(self.tags.values())

    async def create_tag(
        self,
        name: str,
        color: str | None = None,
        parent: str | None = None,
    ) -> Tag:
        """Mock create tag."""
        self._record_call("create_tag", (name,), {"color": color, "parent": parent})
        self._check_failure("create_tag")

        tag = TagFactory.create(label=name, color=color, parent=parent)
        self.tags[tag.name] = tag
        return tag

    async def delete_tag(self, name: str) -> None:
        """Mock delete tag."""
        self._record_call("delete_tag", (name,), {})
        self._check_failure("delete_tag")

        tag_name = name.lower()
        if tag_name not in self.tags:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Tag not found: {name}")

        del self.tags[tag_name]
        # Remove tag from tasks
        for task in self.tasks.values():
            task.tags = [t for t in task.tags if t.lower() != tag_name]

    async def rename_tag(self, old_name: str, new_name: str) -> None:
        """Mock rename tag."""
        self._record_call("rename_tag", (old_name, new_name), {})
        self._check_failure("rename_tag")

        old_tag_name = old_name.lower()
        if old_tag_name not in self.tags:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Tag not found: {old_name}")

        tag = self.tags.pop(old_tag_name)
        new_tag_name = new_name.lower()
        tag.name = new_tag_name
        tag.label = new_name
        self.tags[new_tag_name] = tag

        # Update tag references in tasks
        for task in self.tasks.values():
            task.tags = [new_tag_name if t.lower() == old_tag_name else t for t in task.tags]

    async def merge_tags(self, source: str, target: str) -> None:
        """Mock merge tags."""
        self._record_call("merge_tags", (source, target), {})
        self._check_failure("merge_tags")

        source_name = source.lower()
        target_name = target.lower()

        if source_name not in self.tags:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Source tag not found: {source}")
        if target_name not in self.tags:
            from ticktick_mcp.exceptions import TickTickNotFoundError
            raise TickTickNotFoundError(f"Target tag not found: {target}")

        # Move tasks from source to target
        for task in self.tasks.values():
            if source_name in [t.lower() for t in task.tags]:
                task.tags = [t for t in task.tags if t.lower() != source_name]
                if target_name not in [t.lower() for t in task.tags]:
                    task.tags.append(target_name)

        del self.tags[source_name]

    # -------------------------------------------------------------------------
    # User Operations
    # -------------------------------------------------------------------------

    async def get_user_profile(self) -> User:
        """Mock get user profile."""
        self._record_call("get_user_profile", (), {})
        self._check_failure("get_user_profile")
        return self.user

    async def get_user_status(self) -> UserStatus:
        """Mock get user status."""
        self._record_call("get_user_status", (), {})
        self._check_failure("get_user_status")
        return self.user_status

    async def get_user_statistics(self) -> UserStatistics:
        """Mock get user statistics."""
        self._record_call("get_user_statistics", (), {})
        self._check_failure("get_user_statistics")
        return self.user_statistics

    # -------------------------------------------------------------------------
    # Focus Operations
    # -------------------------------------------------------------------------

    async def get_focus_heatmap(
        self,
        start_date,
        end_date,
    ) -> list[dict[str, Any]]:
        """Mock get focus heatmap."""
        self._record_call("get_focus_heatmap", (start_date, end_date), {})
        self._check_failure("get_focus_heatmap")
        return [{"duration": 3600}, {"duration": 7200}]

    async def get_focus_by_tag(
        self,
        start_date,
        end_date,
    ) -> dict[str, int]:
        """Mock get focus by tag."""
        self._record_call("get_focus_by_tag", (start_date, end_date), {})
        self._check_failure("get_focus_by_tag")
        return {"work": 7200, "study": 3600}

    # -------------------------------------------------------------------------
    # Sync Operations
    # -------------------------------------------------------------------------

    async def sync_all(self) -> dict[str, Any]:
        """Mock full sync."""
        self._record_call("sync_all", (), {})
        self._check_failure("sync_all")

        return {
            "inboxId": self.inbox_id,
            "projectProfiles": [p.model_dump() for p in self.projects.values()],
            "syncTaskBean": {
                "update": [t.model_dump() for t in self.tasks.values()],
            },
            "tags": [t.model_dump() for t in self.tags.values()],
            "projectGroups": [f.model_dump() for f in self.folders.values()],
        }

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def seed_data(
        self,
        tasks: int = 5,
        projects: int = 3,
        folders: int = 2,
        tags: int = 4,
    ) -> None:
        """Seed mock with test data."""
        # Create folders
        for i in range(folders):
            folder = FolderFactory.create(name=f"Folder {i+1}")
            self.folders[folder.id] = folder

        # Create projects
        folder_ids = list(self.folders.keys())
        for i in range(projects):
            group_id = folder_ids[i % len(folder_ids)] if folder_ids else None
            project = ProjectFactory.create(name=f"Project {i+1}", group_id=group_id)
            self.projects[project.id] = project

        # Create tags
        tag_labels = ["work", "personal", "urgent", "later"][:tags]
        for label in tag_labels:
            tag = TagFactory.create(label=label)
            self.tags[tag.name] = tag

        # Create tasks
        project_ids = list(self.projects.keys())
        tag_names = list(self.tags.keys())
        for i in range(tasks):
            project_id = project_ids[i % len(project_ids)] if project_ids else self.inbox_id
            task_tags = [tag_names[i % len(tag_names)]] if tag_names else []
            task = TaskFactory.create(
                title=f"Task {i+1}",
                project_id=project_id,
                tags=task_tags,
                priority=i % 4 * 2 if i % 4 < 3 else 5,  # Cycles through priorities
            )
            self.tasks[task.id] = task

    def clear_call_history(self) -> None:
        """Clear recorded method calls."""
        self.call_history.clear()

    def get_calls(self, method_name: str) -> list[tuple[tuple, dict]]:
        """Get all calls to a specific method."""
        return [(args, kwargs) for name, args, kwargs in self.call_history if name == method_name]

    def assert_called(self, method_name: str, times: int | None = None) -> None:
        """Assert a method was called (optionally a specific number of times)."""
        calls = self.get_calls(method_name)
        if times is not None:
            assert len(calls) == times, f"Expected {method_name} to be called {times} times, got {len(calls)}"
        else:
            assert len(calls) > 0, f"Expected {method_name} to be called at least once"

    def assert_not_called(self, method_name: str) -> None:
        """Assert a method was not called."""
        calls = self.get_calls(method_name)
        assert len(calls) == 0, f"Expected {method_name} not to be called, but was called {len(calls)} times"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def id_generator():
    """Reset and provide ID generator."""
    IDGenerator.reset()
    return IDGenerator


@pytest.fixture
def mock_api() -> MockUnifiedAPI:
    """Create a fresh mock API instance."""
    return MockUnifiedAPI()


@pytest.fixture
def seeded_mock_api() -> MockUnifiedAPI:
    """Create a mock API instance with seeded test data."""
    api = MockUnifiedAPI()
    api.seed_data(tasks=10, projects=5, folders=3, tags=5)
    return api


@pytest.fixture
async def client(mock_api: MockUnifiedAPI) -> AsyncIterator[TickTickClient]:
    """
    Create a TickTickClient with mocked API.

    This fixture patches the UnifiedTickTickAPI to use our mock,
    allowing tests to run without actual API calls.
    """
    with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
        MockAPIClass.return_value = mock_api

        # Create client with dummy credentials
        client = TickTickClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            v1_access_token="test_access_token",
            username="test@example.com",
            password="test_password",
        )

        # Replace the internal API with our mock
        client._api = mock_api

        await client.connect()
        yield client
        await client.disconnect()


@pytest.fixture
async def seeded_client(seeded_mock_api: MockUnifiedAPI) -> AsyncIterator[TickTickClient]:
    """Create a TickTickClient with seeded test data."""
    with patch("ticktick_mcp.client.client.UnifiedTickTickAPI") as MockAPIClass:
        MockAPIClass.return_value = seeded_mock_api

        client = TickTickClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            v1_access_token="test_access_token",
            username="test@example.com",
            password="test_password",
        )

        client._api = seeded_mock_api

        await client.connect()
        yield client
        await client.disconnect()


# =============================================================================
# Factory Fixtures
# =============================================================================


@pytest.fixture
def task_factory() -> type[TaskFactory]:
    """Provide TaskFactory class."""
    return TaskFactory


@pytest.fixture
def project_factory() -> type[ProjectFactory]:
    """Provide ProjectFactory class."""
    return ProjectFactory


@pytest.fixture
def folder_factory() -> type[FolderFactory]:
    """Provide FolderFactory class."""
    return FolderFactory


@pytest.fixture
def tag_factory() -> type[TagFactory]:
    """Provide TagFactory class."""
    return TagFactory


@pytest.fixture
def user_factory() -> type[UserFactory]:
    """Provide UserFactory class."""
    return UserFactory


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task."""
    return TaskFactory.create(title="Sample Task")


@pytest.fixture
def sample_project() -> Project:
    """Create a sample project."""
    return ProjectFactory.create(name="Sample Project")


@pytest.fixture
def sample_folder() -> ProjectGroup:
    """Create a sample folder."""
    return FolderFactory.create(name="Sample Folder")


@pytest.fixture
def sample_tag() -> Tag:
    """Create a sample tag."""
    return TagFactory.create(label="SampleTag")


@pytest.fixture
def sample_user() -> User:
    """Create a sample user."""
    return UserFactory.create()


@pytest.fixture
def sample_tasks() -> list[Task]:
    """Create a variety of sample tasks."""
    return [
        TaskFactory.create(title="Normal Task"),
        TaskFactory.create_with_due_date(1, title="Due Tomorrow"),
        TaskFactory.create_with_due_date(-1, title="Overdue Task"),
        TaskFactory.create_completed(title="Completed Task"),
        TaskFactory.create_with_subtasks(3, title="Task with Subtasks"),
        TaskFactory.create_with_tags(["work", "urgent"], title="Tagged Task"),
        TaskFactory.create_recurring(title="Recurring Task"),
        TaskFactory.create(title="High Priority", priority=TaskPriority.HIGH),
        TaskFactory.create(title="Low Priority", priority=TaskPriority.LOW),
    ]


@pytest.fixture
def priority_tasks() -> list[Task]:
    """Create tasks of each priority level."""
    return TaskFactory.create_priority_set()


# =============================================================================
# Parametrization Helpers
# =============================================================================


PRIORITY_LEVELS = [
    (TaskPriority.NONE, "none"),
    (TaskPriority.LOW, "low"),
    (TaskPriority.MEDIUM, "medium"),
    (TaskPriority.HIGH, "high"),
]

PRIORITY_NAMES = ["none", "low", "medium", "high"]
PRIORITY_VALUES = [0, 1, 3, 5]

VIEW_MODES = ["list", "kanban", "timeline"]
PROJECT_KINDS = ["TASK", "NOTE"]

TASK_STATUSES = [
    (TaskStatus.ABANDONED, "abandoned"),
    (TaskStatus.ACTIVE, "active"),
    (TaskStatus.COMPLETED, "completed"),
]

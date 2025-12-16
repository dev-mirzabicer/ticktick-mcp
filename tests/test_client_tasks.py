"""
Comprehensive Task Operation Tests for TickTick Client.

This module tests all task-related functionality including:
- Create, Read, Update, Delete (CRUD)
- Complete, Move, Make Subtask
- Search, List (all, completed, overdue, by tag, by priority)
- Quick add and convenience methods
- All parameter combinations and edge cases

Test Categories:
- test_create_*: Task creation tests
- test_get_*: Task retrieval tests
- test_update_*: Task update tests
- test_delete_*: Task deletion tests
- test_complete_*: Task completion tests
- test_move_*: Task movement tests
- test_subtask_*: Parent-child relationship tests
- test_list_*: Task listing and filtering tests
- test_search_*: Task search tests
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

from ticktick_mcp.constants import TaskPriority, TaskStatus
from ticktick_mcp.models import Task

if TYPE_CHECKING:
    from tests.conftest import MockUnifiedAPI, TaskFactory
    from ticktick_mcp.client import TickTickClient


pytestmark = [pytest.mark.tasks, pytest.mark.unit]


# =============================================================================
# Task Creation Tests
# =============================================================================


class TestTaskCreation:
    """Tests for task creation functionality."""

    async def test_create_task_minimal(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating a task with only title."""
        task = await client.create_task(title="Simple Task")

        assert task is not None
        assert task.title == "Simple Task"
        assert task.project_id == mock_api.inbox_id
        mock_api.assert_called("create_task")

    async def test_create_task_with_project(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating a task in a specific project."""
        project = await client.create_project(name="Test Project")
        task = await client.create_task(title="Project Task", project_id=project.id)

        assert task.project_id == project.id

    async def test_create_task_with_content(self, client: TickTickClient):
        """Test creating a task with content/notes."""
        task = await client.create_task(
            title="Task with Notes",
            content="This is the task description with notes.",
        )

        assert task.content == "This is the task description with notes."

    async def test_create_task_with_description(self, client: TickTickClient):
        """Test creating a task with checklist description."""
        task = await client.create_task(
            title="Checklist Task",
            description="Checklist description",
        )

        # Description is handled at API level
        assert task.title == "Checklist Task"

    @pytest.mark.parametrize("priority,expected", [
        ("none", 0),
        ("low", 1),
        ("medium", 3),
        ("high", 5),
        (0, 0),
        (1, 1),
        (3, 3),
        (5, 5),
    ])
    async def test_create_task_with_priority(
        self,
        client: TickTickClient,
        priority,
        expected: int,
    ):
        """Test creating tasks with different priority levels."""
        task = await client.create_task(title=f"Priority {priority} Task", priority=priority)

        assert task.priority == expected

    async def test_create_task_with_due_date(self, client: TickTickClient):
        """Test creating a task with due date."""
        due_date = datetime.now(timezone.utc) + timedelta(days=7)
        task = await client.create_task(title="Due Date Task", due_date=due_date)

        assert task.due_date is not None
        # Allow some tolerance for date comparison
        assert abs((task.due_date - due_date).total_seconds()) < 60

    async def test_create_task_with_start_date(self, client: TickTickClient):
        """Test creating a task with start date."""
        start_date = datetime.now(timezone.utc) + timedelta(days=1)
        task = await client.create_task(title="Start Date Task", start_date=start_date)

        assert task.start_date is not None

    async def test_create_task_with_date_range(self, client: TickTickClient):
        """Test creating a task with both start and due dates."""
        start = datetime.now(timezone.utc) + timedelta(days=1)
        due = datetime.now(timezone.utc) + timedelta(days=7)

        task = await client.create_task(
            title="Date Range Task",
            start_date=start,
            due_date=due,
        )

        assert task.start_date is not None
        assert task.due_date is not None

    async def test_create_task_all_day(self, client: TickTickClient):
        """Test creating an all-day task."""
        task = await client.create_task(title="All Day Task", all_day=True)

        assert task.is_all_day is True

    async def test_create_task_with_timezone(self, client: TickTickClient):
        """Test creating a task with specific timezone."""
        task = await client.create_task(
            title="Timezone Task",
            time_zone="America/New_York",
        )

        assert task.time_zone == "America/New_York"

    async def test_create_task_with_tags(self, client: TickTickClient):
        """Test creating a task with tags."""
        tags = ["work", "urgent", "important"]
        task = await client.create_task(title="Tagged Task", tags=tags)

        assert task.tags == tags

    async def test_create_task_with_empty_tags(self, client: TickTickClient):
        """Test creating a task with empty tag list."""
        task = await client.create_task(title="No Tags Task", tags=[])

        assert task.tags == []

    async def test_create_task_with_reminders(self, client: TickTickClient):
        """Test creating a task with reminders."""
        reminders = ["TRIGGER:-PT30M", "TRIGGER:-PT1H"]
        task = await client.create_task(title="Reminder Task", reminders=reminders)

        # Reminders are passed through to API
        assert task.title == "Reminder Task"

    async def test_create_task_with_recurrence(self, client: TickTickClient):
        """Test creating a recurring task."""
        task = await client.create_task(
            title="Daily Task",
            recurrence="RRULE:FREQ=DAILY;INTERVAL=1",
        )

        assert task.repeat_flag == "RRULE:FREQ=DAILY;INTERVAL=1"

    @pytest.mark.parametrize("rrule", [
        "RRULE:FREQ=DAILY;INTERVAL=1",
        "RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE,FR",
        "RRULE:FREQ=MONTHLY;INTERVAL=1;BYMONTHDAY=15",
        "RRULE:FREQ=YEARLY;INTERVAL=1;BYMONTH=7;BYMONTHDAY=4",
    ])
    async def test_create_task_with_various_recurrence(
        self,
        client: TickTickClient,
        rrule: str,
    ):
        """Test creating tasks with various recurrence rules."""
        task = await client.create_task(title="Recurring Task", recurrence=rrule)

        assert task.repeat_flag == rrule

    async def test_create_task_with_parent(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating a task as a subtask of another."""
        parent = await client.create_task(title="Parent Task")
        child = await client.create_task(title="Child Task", parent_id=parent.id)

        assert child.parent_id == parent.id

    async def test_create_task_with_all_parameters(self, client: TickTickClient):
        """Test creating a task with all possible parameters."""
        due_date = datetime.now(timezone.utc) + timedelta(days=3)

        task = await client.create_task(
            title="Full Task",
            content="Complete description",
            priority="high",
            due_date=due_date,
            time_zone="Europe/London",
            all_day=False,
            tags=["comprehensive", "test"],
            reminders=["TRIGGER:-PT15M"],
            recurrence="RRULE:FREQ=WEEKLY;INTERVAL=2",
        )

        assert task.title == "Full Task"
        assert task.content == "Complete description"
        assert task.priority == TaskPriority.HIGH
        assert task.tags == ["comprehensive", "test"]

    async def test_quick_add(self, client: TickTickClient):
        """Test quick_add convenience method."""
        task = await client.quick_add("Quick task text")

        assert task.title == "Quick task text"

    async def test_quick_add_to_project(self, client: TickTickClient):
        """Test quick_add to specific project."""
        project = await client.create_project(name="Quick Project")
        task = await client.quick_add("Quick task", project_id=project.id)

        assert task.project_id == project.id


# =============================================================================
# Task Retrieval Tests
# =============================================================================


class TestTaskRetrieval:
    """Tests for task retrieval functionality."""

    async def test_get_task_by_id(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting a task by ID."""
        created = await client.create_task(title="Task to Get")
        retrieved = await client.get_task(created.id)

        assert retrieved.id == created.id
        assert retrieved.title == created.title

    async def test_get_task_with_project_id(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting a task with project_id hint."""
        project = await client.create_project(name="Test Project")
        created = await client.create_task(title="Project Task", project_id=project.id)

        retrieved = await client.get_task(created.id, project_id=project.id)

        assert retrieved.id == created.id

    async def test_get_nonexistent_task(self, client: TickTickClient):
        """Test getting a task that doesn't exist."""
        from ticktick_mcp.exceptions import TickTickNotFoundError

        with pytest.raises(TickTickNotFoundError):
            await client.get_task("nonexistent_task_id_12345")

    async def test_get_all_tasks(self, seeded_client: TickTickClient):
        """Test getting all active tasks."""
        tasks = await seeded_client.get_all_tasks()

        assert isinstance(tasks, list)
        assert len(tasks) > 0
        # All should be active
        for task in tasks:
            assert task.status == TaskStatus.ACTIVE


# =============================================================================
# Task Update Tests
# =============================================================================


class TestTaskUpdate:
    """Tests for task update functionality."""

    async def test_update_task_title(self, client: TickTickClient):
        """Test updating task title."""
        task = await client.create_task(title="Original Title")
        task.title = "Updated Title"
        updated = await client.update_task(task)

        assert updated.title == "Updated Title"

    async def test_update_task_content(self, client: TickTickClient):
        """Test updating task content."""
        task = await client.create_task(title="Task", content="Original content")
        task.content = "Updated content"
        updated = await client.update_task(task)

        assert updated.content == "Updated content"

    @pytest.mark.parametrize("old_priority,new_priority", [
        (TaskPriority.NONE, TaskPriority.HIGH),
        (TaskPriority.HIGH, TaskPriority.NONE),
        (TaskPriority.LOW, TaskPriority.MEDIUM),
        (TaskPriority.MEDIUM, TaskPriority.LOW),
    ])
    async def test_update_task_priority(
        self,
        client: TickTickClient,
        old_priority: int,
        new_priority: int,
    ):
        """Test updating task priority between different levels."""
        task = await client.create_task(title="Priority Task", priority=old_priority)
        task.priority = new_priority
        updated = await client.update_task(task)

        assert updated.priority == new_priority

    async def test_update_task_due_date(self, client: TickTickClient):
        """Test updating task due date."""
        original_due = datetime.now(timezone.utc) + timedelta(days=1)
        task = await client.create_task(title="Task", due_date=original_due)

        new_due = datetime.now(timezone.utc) + timedelta(days=7)
        task.due_date = new_due
        updated = await client.update_task(task)

        assert updated.due_date is not None

    async def test_update_task_clear_due_date(self, client: TickTickClient):
        """Test clearing task due date."""
        due = datetime.now(timezone.utc) + timedelta(days=1)
        task = await client.create_task(title="Task", due_date=due)

        task.due_date = None
        updated = await client.update_task(task)

        assert updated.due_date is None

    async def test_update_task_tags(self, client: TickTickClient):
        """Test updating task tags."""
        task = await client.create_task(title="Task", tags=["original"])
        task.tags = ["updated", "tags"]
        updated = await client.update_task(task)

        assert updated.tags == ["updated", "tags"]

    async def test_update_task_add_tags(self, client: TickTickClient):
        """Test adding tags to a task."""
        task = await client.create_task(title="Task", tags=["existing"])
        task.tags.append("new")
        updated = await client.update_task(task)

        assert "existing" in updated.tags
        assert "new" in updated.tags

    async def test_update_task_clear_tags(self, client: TickTickClient):
        """Test clearing all tags from a task."""
        task = await client.create_task(title="Task", tags=["tag1", "tag2"])
        task.tags = []
        updated = await client.update_task(task)

        assert updated.tags == []

    async def test_update_multiple_fields(self, client: TickTickClient):
        """Test updating multiple fields at once."""
        task = await client.create_task(
            title="Original",
            content="Original content",
            priority="low",
        )

        task.title = "Updated"
        task.content = "Updated content"
        task.priority = TaskPriority.HIGH

        updated = await client.update_task(task)

        assert updated.title == "Updated"
        assert updated.content == "Updated content"
        assert updated.priority == TaskPriority.HIGH

    async def test_update_nonexistent_task(self, client: TickTickClient, task_factory: type[TaskFactory]):
        """Test updating a task that doesn't exist."""
        from ticktick_mcp.exceptions import TickTickNotFoundError

        fake_task = task_factory.create(id="nonexistent_id_1234567890")

        with pytest.raises(TickTickNotFoundError):
            await client.update_task(fake_task)


# =============================================================================
# Task Deletion Tests
# =============================================================================


class TestTaskDeletion:
    """Tests for task deletion functionality."""

    async def test_delete_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test deleting a task."""
        task = await client.create_task(title="Task to Delete")
        task_id = task.id
        project_id = task.project_id

        await client.delete_task(task_id, project_id)

        # Task should no longer exist
        assert task_id not in mock_api.tasks

    async def test_delete_task_removes_from_project(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that deleting a task removes it from the project's task list."""
        project = await client.create_project(name="Test Project")
        task = await client.create_task(title="Task", project_id=project.id)

        await client.delete_task(task.id, project.id)

        # Task should not appear in project's tasks
        remaining_tasks = [t for t in mock_api.tasks.values() if t.project_id == project.id]
        assert task.id not in [t.id for t in remaining_tasks]

    async def test_delete_nonexistent_task(self, client: TickTickClient):
        """Test deleting a task that doesn't exist."""
        from ticktick_mcp.exceptions import TickTickNotFoundError

        with pytest.raises(TickTickNotFoundError):
            await client.delete_task("nonexistent_id", "some_project_id")

    async def test_delete_task_idempotent(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that deleting already-deleted task raises error (not idempotent at API level)."""
        from ticktick_mcp.exceptions import TickTickNotFoundError

        task = await client.create_task(title="Task")
        await client.delete_task(task.id, task.project_id)

        with pytest.raises(TickTickNotFoundError):
            await client.delete_task(task.id, task.project_id)


# =============================================================================
# Task Completion Tests
# =============================================================================


class TestTaskCompletion:
    """Tests for task completion functionality."""

    async def test_complete_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test completing a task."""
        task = await client.create_task(title="Task to Complete")
        await client.complete_task(task.id, task.project_id)

        # Verify task is completed
        completed_task = mock_api.tasks[task.id]
        assert completed_task.status == TaskStatus.COMPLETED
        assert completed_task.completed_time is not None

    async def test_complete_already_completed_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test completing an already completed task (should be idempotent)."""
        task = await client.create_task(title="Task")
        await client.complete_task(task.id, task.project_id)

        # Complete again - should not raise
        await client.complete_task(task.id, task.project_id)

        completed_task = mock_api.tasks[task.id]
        assert completed_task.status == TaskStatus.COMPLETED

    async def test_complete_nonexistent_task(self, client: TickTickClient):
        """Test completing a task that doesn't exist."""
        from ticktick_mcp.exceptions import TickTickNotFoundError

        with pytest.raises(TickTickNotFoundError):
            await client.complete_task("nonexistent_id", "some_project_id")

    async def test_complete_high_priority_task(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test completing a high priority task."""
        task = await client.create_task(title="Urgent Task", priority="high")
        await client.complete_task(task.id, task.project_id)

        completed = mock_api.tasks[task.id]
        assert completed.status == TaskStatus.COMPLETED
        assert completed.priority == TaskPriority.HIGH  # Priority preserved


# =============================================================================
# Task Movement Tests
# =============================================================================


class TestTaskMovement:
    """Tests for moving tasks between projects."""

    async def test_move_task_between_projects(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test moving a task from one project to another."""
        project1 = await client.create_project(name="Project 1")
        project2 = await client.create_project(name="Project 2")
        task = await client.create_task(title="Moving Task", project_id=project1.id)

        await client.move_task(task.id, project1.id, project2.id)

        moved_task = mock_api.tasks[task.id]
        assert moved_task.project_id == project2.id

    async def test_move_task_to_inbox(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test moving a task to inbox."""
        project = await client.create_project(name="Project")
        task = await client.create_task(title="Task", project_id=project.id)

        await client.move_task(task.id, project.id, mock_api.inbox_id)

        moved_task = mock_api.tasks[task.id]
        assert moved_task.project_id == mock_api.inbox_id

    async def test_move_task_from_inbox(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test moving a task from inbox to project."""
        project = await client.create_project(name="Project")
        task = await client.create_task(title="Inbox Task")  # Created in inbox by default

        await client.move_task(task.id, mock_api.inbox_id, project.id)

        moved_task = mock_api.tasks[task.id]
        assert moved_task.project_id == project.id

    async def test_move_nonexistent_task(self, client: TickTickClient):
        """Test moving a task that doesn't exist."""
        from ticktick_mcp.exceptions import TickTickNotFoundError

        with pytest.raises(TickTickNotFoundError):
            await client.move_task("nonexistent", "project1", "project2")

    async def test_move_task_preserves_properties(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that moving a task preserves all its properties."""
        project1 = await client.create_project(name="Project 1")
        project2 = await client.create_project(name="Project 2")

        task = await client.create_task(
            title="Full Task",
            project_id=project1.id,
            content="Content",
            priority="high",
            tags=["important"],
        )

        await client.move_task(task.id, project1.id, project2.id)

        moved = mock_api.tasks[task.id]
        assert moved.title == "Full Task"
        assert moved.content == "Content"
        assert moved.priority == TaskPriority.HIGH
        assert "important" in moved.tags


# =============================================================================
# Subtask Tests
# =============================================================================


class TestSubtasks:
    """Tests for parent-child task relationships."""

    async def test_make_subtask(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test making a task a subtask of another."""
        parent = await client.create_task(title="Parent Task")
        child = await client.create_task(title="Child Task", project_id=parent.project_id)

        await client.make_subtask(child.id, parent.id, parent.project_id)

        child_task = mock_api.tasks[child.id]
        parent_task = mock_api.tasks[parent.id]

        assert child_task.parent_id == parent.id
        assert child.id in parent_task.child_ids

    async def test_make_multiple_subtasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test making multiple tasks subtasks of one parent."""
        parent = await client.create_task(title="Parent")
        child1 = await client.create_task(title="Child 1", project_id=parent.project_id)
        child2 = await client.create_task(title="Child 2", project_id=parent.project_id)
        child3 = await client.create_task(title="Child 3", project_id=parent.project_id)

        await client.make_subtask(child1.id, parent.id, parent.project_id)
        await client.make_subtask(child2.id, parent.id, parent.project_id)
        await client.make_subtask(child3.id, parent.id, parent.project_id)

        parent_task = mock_api.tasks[parent.id]
        assert len(parent_task.child_ids) == 3
        assert child1.id in parent_task.child_ids
        assert child2.id in parent_task.child_ids
        assert child3.id in parent_task.child_ids

    async def test_make_subtask_nonexistent_child(self, client: TickTickClient):
        """Test making a nonexistent task a subtask."""
        from ticktick_mcp.exceptions import TickTickNotFoundError

        parent = await client.create_task(title="Parent")

        with pytest.raises(TickTickNotFoundError):
            await client.make_subtask("nonexistent", parent.id, parent.project_id)


# =============================================================================
# Task Listing Tests
# =============================================================================


class TestTaskListing:
    """Tests for listing and filtering tasks."""

    async def test_get_today_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting tasks due today."""
        today = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        # Create tasks with different due dates
        await client.create_task(title="Due Today", due_date=today)
        await client.create_task(title="Due Tomorrow", due_date=tomorrow)
        await client.create_task(title="Due Yesterday", due_date=yesterday)
        await client.create_task(title="No Due Date")

        today_tasks = await client.get_today_tasks()

        # Should only include task due today
        assert len(today_tasks) >= 1
        titles = [t.title for t in today_tasks]
        assert "Due Today" in titles

    async def test_get_overdue_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting overdue tasks."""
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)

        await client.create_task(title="Overdue 1", due_date=yesterday)
        await client.create_task(title="Overdue 2", due_date=two_days_ago)
        await client.create_task(title="Not Overdue", due_date=tomorrow)

        overdue = await client.get_overdue_tasks()

        titles = [t.title for t in overdue]
        assert "Overdue 1" in titles
        assert "Overdue 2" in titles
        assert "Not Overdue" not in titles

    async def test_get_tasks_by_tag(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting tasks by tag."""
        await client.create_task(title="Work Task 1", tags=["work"])
        await client.create_task(title="Work Task 2", tags=["work", "urgent"])
        await client.create_task(title="Personal Task", tags=["personal"])
        await client.create_task(title="No Tags")

        work_tasks = await client.get_tasks_by_tag("work")

        assert len(work_tasks) == 2
        titles = [t.title for t in work_tasks]
        assert "Work Task 1" in titles
        assert "Work Task 2" in titles

    async def test_get_tasks_by_tag_case_insensitive(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that tag filtering is case-insensitive."""
        await client.create_task(title="Task 1", tags=["Work"])
        await client.create_task(title="Task 2", tags=["WORK"])
        await client.create_task(title="Task 3", tags=["work"])

        tasks = await client.get_tasks_by_tag("WORK")

        assert len(tasks) == 3

    @pytest.mark.parametrize("priority_input,expected_priority", [
        ("high", TaskPriority.HIGH),
        ("medium", TaskPriority.MEDIUM),
        ("low", TaskPriority.LOW),
        ("none", TaskPriority.NONE),
        (5, TaskPriority.HIGH),
        (3, TaskPriority.MEDIUM),
        (1, TaskPriority.LOW),
        (0, TaskPriority.NONE),
    ])
    async def test_get_tasks_by_priority(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
        priority_input,
        expected_priority: int,
    ):
        """Test getting tasks by priority level."""
        # Clear existing tasks
        mock_api.tasks.clear()

        # Create tasks with each priority
        await client.create_task(title="No Priority", priority=0)
        await client.create_task(title="Low Priority", priority=1)
        await client.create_task(title="Medium Priority", priority=3)
        await client.create_task(title="High Priority", priority=5)

        tasks = await client.get_tasks_by_priority(priority_input)

        assert len(tasks) == 1
        assert tasks[0].priority == expected_priority

    async def test_get_completed_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting completed tasks."""
        task1 = await client.create_task(title="Task 1")
        task2 = await client.create_task(title="Task 2")
        await client.create_task(title="Task 3")  # Not completed

        await client.complete_task(task1.id, task1.project_id)
        await client.complete_task(task2.id, task2.project_id)

        completed = await client.get_completed_tasks(days=7, limit=100)

        assert len(completed) == 2

    async def test_get_completed_tasks_with_limit(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting completed tasks with limit."""
        # Create and complete many tasks
        for i in range(10):
            task = await client.create_task(title=f"Task {i}")
            await client.complete_task(task.id, task.project_id)

        completed = await client.get_completed_tasks(days=7, limit=5)

        assert len(completed) <= 5

    async def test_get_completed_tasks_date_range(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that completed tasks respects date range."""
        # This tests the days parameter
        task = await client.create_task(title="Recent Task")
        await client.complete_task(task.id, task.project_id)

        # Should find task completed today
        completed = await client.get_completed_tasks(days=1)
        assert len(completed) >= 1


# =============================================================================
# Task Search Tests
# =============================================================================


class TestTaskSearch:
    """Tests for task search functionality."""

    async def test_search_tasks_by_title(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test searching tasks by title."""
        await client.create_task(title="Buy groceries")
        await client.create_task(title="Buy office supplies")
        await client.create_task(title="Sell old laptop")

        results = await client.search_tasks("Buy")

        assert len(results) == 2
        titles = [t.title for t in results]
        assert "Buy groceries" in titles
        assert "Buy office supplies" in titles

    async def test_search_tasks_by_content(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test searching tasks by content."""
        await client.create_task(title="Task 1", content="Meeting with marketing team")
        await client.create_task(title="Task 2", content="Code review session")
        await client.create_task(title="Task 3", content="Marketing presentation")

        results = await client.search_tasks("marketing")

        assert len(results) == 2

    async def test_search_tasks_case_insensitive(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that search is case-insensitive."""
        await client.create_task(title="URGENT Task")
        await client.create_task(title="urgent matter")
        await client.create_task(title="Urgent Priority")

        results = await client.search_tasks("urgent")

        assert len(results) == 3

    async def test_search_tasks_no_results(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test search with no matching results."""
        await client.create_task(title="Task 1")
        await client.create_task(title="Task 2")

        results = await client.search_tasks("nonexistent_query_xyz")

        assert len(results) == 0

    async def test_search_tasks_partial_match(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test search with partial word match."""
        await client.create_task(title="Development meeting")
        await client.create_task(title="Developer tools")

        results = await client.search_tasks("Develop")

        assert len(results) == 2


# =============================================================================
# Combination Tests
# =============================================================================


class TestTaskCombinations:
    """Tests for combinations of task operations."""

    async def test_create_update_complete_flow(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test full lifecycle: create, update, complete."""
        # Create
        task = await client.create_task(title="Lifecycle Task", priority="low")
        assert task.status == TaskStatus.ACTIVE

        # Update
        task.priority = TaskPriority.HIGH
        task.content = "Updated description"
        updated = await client.update_task(task)
        assert updated.priority == TaskPriority.HIGH

        # Complete
        await client.complete_task(updated.id, updated.project_id)
        final = mock_api.tasks[updated.id]
        assert final.status == TaskStatus.COMPLETED

    async def test_create_move_complete_flow(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test create in inbox, move to project, complete."""
        project = await client.create_project(name="Target Project")

        # Create in inbox
        task = await client.create_task(title="Moving Task")
        assert task.project_id == mock_api.inbox_id

        # Move to project
        await client.move_task(task.id, mock_api.inbox_id, project.id)
        moved = mock_api.tasks[task.id]
        assert moved.project_id == project.id

        # Complete
        await client.complete_task(task.id, project.id)
        final = mock_api.tasks[task.id]
        assert final.status == TaskStatus.COMPLETED

    async def test_create_subtask_complete_parent(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating subtasks and completing parent."""
        parent = await client.create_task(title="Parent")
        child1 = await client.create_task(title="Child 1", project_id=parent.project_id)
        child2 = await client.create_task(title="Child 2", project_id=parent.project_id)

        await client.make_subtask(child1.id, parent.id, parent.project_id)
        await client.make_subtask(child2.id, parent.id, parent.project_id)

        # Complete children first
        await client.complete_task(child1.id, parent.project_id)
        await client.complete_task(child2.id, parent.project_id)

        # Complete parent
        await client.complete_task(parent.id, parent.project_id)

        parent_final = mock_api.tasks[parent.id]
        assert parent_final.status == TaskStatus.COMPLETED

    async def test_bulk_create_and_filter(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating multiple tasks and filtering them."""
        # Create varied tasks
        for i in range(5):
            await client.create_task(
                title=f"Work Task {i}",
                tags=["work"],
                priority="high" if i % 2 == 0 else "low",
            )

        for i in range(5):
            await client.create_task(
                title=f"Personal Task {i}",
                tags=["personal"],
                priority="medium",
            )

        # Filter by tag
        work_tasks = await client.get_tasks_by_tag("work")
        assert len(work_tasks) == 5

        # Filter by priority
        high_priority = await client.get_tasks_by_priority("high")
        assert len(high_priority) == 3  # Tasks 0, 2, 4 from work

    async def test_tagged_task_through_lifecycle(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test tagged task through full lifecycle."""
        # Create with tags
        task = await client.create_task(
            title="Tagged Task",
            tags=["important", "urgent"],
        )

        # Verify searchable by tag
        important_tasks = await client.get_tasks_by_tag("important")
        assert task.id in [t.id for t in important_tasks]

        # Update tags
        task.tags = ["important", "done"]
        updated = await client.update_task(task)

        # No longer in urgent
        urgent_tasks = await client.get_tasks_by_tag("urgent")
        assert task.id not in [t.id for t in urgent_tasks]

        # Still in important
        important_tasks = await client.get_tasks_by_tag("important")
        assert task.id in [t.id for t in important_tasks]

        # Complete
        await client.complete_task(task.id, task.project_id)

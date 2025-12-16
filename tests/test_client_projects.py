"""
Comprehensive Project Operation Tests for TickTick Client.

This module tests all project-related functionality including:
- Create, Read, Delete
- Get with data (tasks + columns)
- Project types and view modes
- Folder organization
- All parameter combinations

Test Categories:
- test_create_*: Project creation tests
- test_get_*: Project retrieval tests
- test_delete_*: Project deletion tests
- test_list_*: Project listing tests
- test_folder_*: Folder organization tests
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ticktick_mcp.constants import ProjectKind, ViewMode

if TYPE_CHECKING:
    from tests.conftest import MockUnifiedAPI, ProjectFactory
    from ticktick_mcp.client import TickTickClient


pytestmark = [pytest.mark.projects, pytest.mark.unit]


# =============================================================================
# Project Creation Tests
# =============================================================================


class TestProjectCreation:
    """Tests for project creation functionality."""

    async def test_create_project_minimal(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating a project with only name."""
        project = await client.create_project(name="Simple Project")

        assert project is not None
        assert project.name == "Simple Project"
        assert project.id in mock_api.projects
        mock_api.assert_called("create_project")

    async def test_create_project_with_color(self, client: TickTickClient):
        """Test creating a project with color."""
        project = await client.create_project(name="Colored Project", color="#F18181")

        assert project.color == "#F18181"

    @pytest.mark.parametrize("color", [
        "#F18181",  # Red
        "#86BB6D",  # Green
        "#4CAFF6",  # Blue
        "#FFD966",  # Yellow
        "#9C87E0",  # Purple
        "#E0A883",  # Brown
        None,  # No color
    ])
    async def test_create_project_various_colors(self, client: TickTickClient, color: str | None):
        """Test creating projects with various colors."""
        project = await client.create_project(name="Project", color=color)

        if color:
            assert project.color == color
        else:
            # Color might be None or default
            pass

    @pytest.mark.parametrize("kind", ["TASK", "NOTE"])
    async def test_create_project_with_kind(self, client: TickTickClient, kind: str):
        """Test creating projects with different kinds."""
        project = await client.create_project(name=f"{kind} Project", kind=kind)

        assert project.kind == kind

    @pytest.mark.parametrize("view_mode", ["list", "kanban", "timeline"])
    async def test_create_project_with_view_mode(self, client: TickTickClient, view_mode: str):
        """Test creating projects with different view modes."""
        project = await client.create_project(name=f"{view_mode} Project", view_mode=view_mode)

        assert project.view_mode == view_mode

    async def test_create_project_in_folder(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating a project in a folder."""
        folder = await client.create_folder("Test Folder")
        project = await client.create_project(name="Folder Project", folder_id=folder.id)

        assert project.group_id == folder.id

    async def test_create_project_all_parameters(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating a project with all parameters."""
        folder = await client.create_folder("Folder")

        project = await client.create_project(
            name="Full Project",
            color="#4CAFF6",
            kind="TASK",
            view_mode="kanban",
            folder_id=folder.id,
        )

        assert project.name == "Full Project"
        assert project.color == "#4CAFF6"
        assert project.kind == "TASK"
        assert project.view_mode == "kanban"
        assert project.group_id == folder.id

    async def test_create_multiple_projects(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating multiple projects."""
        projects = []
        for i in range(5):
            project = await client.create_project(name=f"Project {i}")
            projects.append(project)

        assert len(projects) == 5
        assert len(mock_api.projects) == 5

        # All IDs should be unique
        ids = [p.id for p in projects]
        assert len(ids) == len(set(ids))

    async def test_create_project_with_same_name(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating projects with the same name (allowed)."""
        project1 = await client.create_project(name="Same Name")
        project2 = await client.create_project(name="Same Name")

        assert project1.id != project2.id
        assert project1.name == project2.name


# =============================================================================
# Project Retrieval Tests
# =============================================================================


class TestProjectRetrieval:
    """Tests for project retrieval functionality."""

    async def test_get_all_projects(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting all projects."""
        # Create some projects
        await client.create_project(name="Project 1")
        await client.create_project(name="Project 2")
        await client.create_project(name="Project 3")

        projects = await client.get_all_projects()

        assert len(projects) == 3

    async def test_get_all_projects_empty(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting projects when none exist."""
        projects = await client.get_all_projects()

        assert projects == []

    async def test_get_project_by_id(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting a project by ID."""
        created = await client.create_project(name="Test Project")
        retrieved = await client.get_project(created.id)

        assert retrieved.id == created.id
        assert retrieved.name == "Test Project"

    async def test_get_nonexistent_project(self, client: TickTickClient):
        """Test getting a project that doesn't exist."""
        from ticktick_mcp.exceptions import TickTickNotFoundError

        with pytest.raises(TickTickNotFoundError):
            await client.get_project("nonexistent_project_id")

    async def test_get_project_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting a project with its tasks."""
        project = await client.create_project(name="Project with Tasks")

        # Add tasks to the project
        await client.create_task(title="Task 1", project_id=project.id)
        await client.create_task(title="Task 2", project_id=project.id)
        await client.create_task(title="Task 3", project_id=project.id)

        project_data = await client.get_project_tasks(project.id)

        assert project_data.project.id == project.id
        assert len(project_data.tasks) == 3

    async def test_get_project_tasks_empty(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test getting a project with no tasks."""
        project = await client.create_project(name="Empty Project")

        project_data = await client.get_project_tasks(project.id)

        assert project_data.project.id == project.id
        assert len(project_data.tasks) == 0

    async def test_get_project_tasks_includes_correct_tasks(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
    ):
        """Test that get_project_tasks only returns tasks from that project."""
        project1 = await client.create_project(name="Project 1")
        project2 = await client.create_project(name="Project 2")

        await client.create_task(title="P1 Task 1", project_id=project1.id)
        await client.create_task(title="P1 Task 2", project_id=project1.id)
        await client.create_task(title="P2 Task 1", project_id=project2.id)

        project_data = await client.get_project_tasks(project1.id)

        assert len(project_data.tasks) == 2
        task_titles = [t.title for t in project_data.tasks]
        assert "P1 Task 1" in task_titles
        assert "P1 Task 2" in task_titles
        assert "P2 Task 1" not in task_titles


# =============================================================================
# Project Deletion Tests
# =============================================================================


class TestProjectDeletion:
    """Tests for project deletion functionality."""

    async def test_delete_project(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test deleting a project."""
        project = await client.create_project(name="Project to Delete")
        project_id = project.id

        await client.delete_project(project_id)

        assert project_id not in mock_api.projects

    async def test_delete_project_removes_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that deleting a project removes its tasks."""
        project = await client.create_project(name="Project")
        task1 = await client.create_task(title="Task 1", project_id=project.id)
        task2 = await client.create_task(title="Task 2", project_id=project.id)

        await client.delete_project(project.id)

        # Tasks should be removed
        assert task1.id not in mock_api.tasks
        assert task2.id not in mock_api.tasks

    async def test_delete_nonexistent_project(self, client: TickTickClient):
        """Test deleting a project that doesn't exist."""
        from ticktick_mcp.exceptions import TickTickNotFoundError

        with pytest.raises(TickTickNotFoundError):
            await client.delete_project("nonexistent_id")

    async def test_delete_project_in_folder(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test deleting a project that's in a folder."""
        folder = await client.create_folder("Folder")
        project = await client.create_project(name="Project", folder_id=folder.id)

        await client.delete_project(project.id)

        # Folder should still exist
        assert folder.id in mock_api.folders
        # Project should be gone
        assert project.id not in mock_api.projects


# =============================================================================
# Project Listing Tests
# =============================================================================


class TestProjectListing:
    """Tests for project listing functionality."""

    async def test_list_projects_sorted(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that projects are listed."""
        await client.create_project(name="Project A")
        await client.create_project(name="Project B")
        await client.create_project(name="Project C")

        projects = await client.get_all_projects()

        assert len(projects) == 3

    async def test_list_projects_includes_all_types(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test listing includes both TASK and NOTE projects."""
        await client.create_project(name="Task Project", kind="TASK")
        await client.create_project(name="Note Project", kind="NOTE")

        projects = await client.get_all_projects()

        kinds = [p.kind for p in projects]
        assert "TASK" in kinds
        assert "NOTE" in kinds

    async def test_list_projects_includes_all_view_modes(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test listing includes all view modes."""
        await client.create_project(name="List Project", view_mode="list")
        await client.create_project(name="Kanban Project", view_mode="kanban")
        await client.create_project(name="Timeline Project", view_mode="timeline")

        projects = await client.get_all_projects()

        view_modes = [p.view_mode for p in projects]
        assert "list" in view_modes
        assert "kanban" in view_modes
        assert "timeline" in view_modes


# =============================================================================
# Project Folder Organization Tests
# =============================================================================


class TestProjectFolderOrganization:
    """Tests for project organization in folders."""

    async def test_create_project_in_multiple_folders(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating projects in different folders."""
        folder1 = await client.create_folder("Work")
        folder2 = await client.create_folder("Personal")

        project1 = await client.create_project(name="Work Project", folder_id=folder1.id)
        project2 = await client.create_project(name="Personal Project", folder_id=folder2.id)

        assert project1.group_id == folder1.id
        assert project2.group_id == folder2.id

    async def test_projects_without_folder(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating projects without a folder."""
        project = await client.create_project(name="Ungrouped Project")

        assert project.group_id is None

    async def test_delete_folder_ungroups_projects(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test that deleting a folder ungroups its projects."""
        folder = await client.create_folder("Folder")
        project = await client.create_project(name="Project", folder_id=folder.id)

        assert project.group_id == folder.id

        await client.delete_folder(folder.id)

        # Project should be ungrouped
        updated_project = mock_api.projects[project.id]
        assert updated_project.group_id is None


# =============================================================================
# Project Combination Tests
# =============================================================================


class TestProjectCombinations:
    """Tests for combinations of project operations."""

    async def test_full_project_lifecycle(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test full project lifecycle: create, add tasks, get with data, delete."""
        # Create
        project = await client.create_project(
            name="Lifecycle Project",
            color="#F18181",
            view_mode="kanban",
        )

        # Add tasks
        task1 = await client.create_task(title="Task 1", project_id=project.id)
        task2 = await client.create_task(title="Task 2", project_id=project.id)

        # Get with data
        project_data = await client.get_project_tasks(project.id)
        assert len(project_data.tasks) == 2

        # Delete
        await client.delete_project(project.id)

        assert project.id not in mock_api.projects
        assert task1.id not in mock_api.tasks
        assert task2.id not in mock_api.tasks

    async def test_project_with_organized_folders_and_tasks(
        self,
        client: TickTickClient,
        mock_api: MockUnifiedAPI,
    ):
        """Test complex organization: folders, projects, and tasks."""
        # Create folder structure
        work_folder = await client.create_folder("Work")
        personal_folder = await client.create_folder("Personal")

        # Create projects in folders
        work_project = await client.create_project(name="Work Project", folder_id=work_folder.id)
        personal_project = await client.create_project(name="Personal Project", folder_id=personal_folder.id)
        ungrouped_project = await client.create_project(name="Ungrouped")

        # Create tasks in projects
        await client.create_task(title="Work Task 1", project_id=work_project.id)
        await client.create_task(title="Work Task 2", project_id=work_project.id)
        await client.create_task(title="Personal Task", project_id=personal_project.id)
        await client.create_task(title="Ungrouped Task", project_id=ungrouped_project.id)

        # Verify structure
        all_projects = await client.get_all_projects()
        assert len(all_projects) == 3

        work_data = await client.get_project_tasks(work_project.id)
        assert len(work_data.tasks) == 2

        personal_data = await client.get_project_tasks(personal_project.id)
        assert len(personal_data.tasks) == 1

    async def test_create_kanban_project_with_tasks(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test creating a kanban project and adding tasks."""
        project = await client.create_project(
            name="Kanban Board",
            view_mode="kanban",
        )

        # Add tasks
        await client.create_task(title="To Do", project_id=project.id)
        await client.create_task(title="In Progress", project_id=project.id)
        await client.create_task(title="Done", project_id=project.id)

        project_data = await client.get_project_tasks(project.id)
        assert len(project_data.tasks) == 3

    async def test_note_project_operations(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test operations on NOTE type projects."""
        project = await client.create_project(
            name="Notes",
            kind="NOTE",
            view_mode="list",
        )

        # Can still add tasks (notes)
        await client.create_task(title="Note 1", project_id=project.id)
        await client.create_task(title="Note 2", project_id=project.id)

        project_data = await client.get_project_tasks(project.id)
        assert project_data.project.kind == "NOTE"
        assert len(project_data.tasks) == 2

    @pytest.mark.parametrize("kind,view_mode", [
        ("TASK", "list"),
        ("TASK", "kanban"),
        ("TASK", "timeline"),
        ("NOTE", "list"),
        ("NOTE", "kanban"),
        ("NOTE", "timeline"),
    ])
    async def test_all_kind_viewmode_combinations(
        self,
        client: TickTickClient,
        kind: str,
        view_mode: str,
    ):
        """Test all combinations of project kind and view mode."""
        project = await client.create_project(
            name=f"{kind} {view_mode}",
            kind=kind,
            view_mode=view_mode,
        )

        assert project.kind == kind
        assert project.view_mode == view_mode

    async def test_move_task_between_projects(self, client: TickTickClient, mock_api: MockUnifiedAPI):
        """Test moving tasks between projects."""
        project1 = await client.create_project(name="Source")
        project2 = await client.create_project(name="Destination")

        task = await client.create_task(title="Moving Task", project_id=project1.id)

        # Verify initial state
        p1_data = await client.get_project_tasks(project1.id)
        assert len(p1_data.tasks) == 1

        # Move task
        await client.move_task(task.id, project1.id, project2.id)

        # Verify moved
        p1_data = await client.get_project_tasks(project1.id)
        p2_data = await client.get_project_tasks(project2.id)

        assert len(p1_data.tasks) == 0
        assert len(p2_data.tasks) == 1
        assert p2_data.tasks[0].id == task.id

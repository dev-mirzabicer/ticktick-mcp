# ticktick-sdk: A TickTick MCP Server & Full Python SDK

![PyPI - Version](https://img.shields.io/pypi/v/ticktick-sdk?color=green)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/ticktick-sdk?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=ORANGE&left_text=downloads)](https://pepy.tech/projects/ticktick-sdk)

A comprehensive async Python SDK for [TickTick](https://ticktick.com) with [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) server support.

**Use TickTick programmatically from Python, or let AI assistants manage your tasks.**

## Table of Contents

- [Features](#features)
- [Why This Library?](#why-this-library)
- [Installation](#installation)
- [MCP Server Setup & Usage](#mcp-server-setup--usage)
  - [Step 1: Register Your App](#step-1-register-your-app)
  - [Step 2: Get OAuth2 Access Token](#step-2-get-oauth2-access-token)
  - [Step 3: Configure Your AI Assistant](#step-3-configure-your-ai-assistant)
  - [CLI Reference](#cli-reference)
  - [Example Conversations](#example-conversations)
  - [Available MCP Tools](#available-mcp-tools-45-total)
- [Python Library Setup & Usage](#python-library-setup--usage)
  - [Setup](#setup)
  - [Quick Start](#quick-start)
  - [Tasks](#tasks)
  - [Projects & Folders](#projects--folders)
  - [Tags](#tags)
  - [Habits](#habits)
  - [Focus/Pomodoro](#focuspomodoro)
  - [User & Statistics](#user--statistics)
  - [Error Handling](#error-handling)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [TickTick API Quirks](#important-ticktick-api-quirks)
- [Environment Variables](#environment-variables)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Features

### MCP Server
- **45 Tools**: Comprehensive coverage of TickTick functionality
- **AI-Ready**: Works with Claude, GPT, and other MCP-compatible assistants
- **Dual Output**: Markdown for humans, JSON for machines

### Python Library
- **Full Async Support**: Built on `httpx` for high-performance async operations
- **Complete Task Management**: Create, read, update, delete, complete, move tasks
- **Project Organization**: Projects, folders, kanban boards
- **Tag System**: Hierarchical tags with colors
- **Habit Tracking**: Full CRUD for habits with check-ins, streaks, and goals
- **Focus/Pomodoro**: Access focus session data and statistics
- **User Analytics**: Productivity scores, levels, completion rates

### Developer Experience
- **Type-Safe**: Full Pydantic v2 validation with comprehensive type hints
- **Well-Tested**: 300+ tests covering both mock and live API interactions
- **Documented**: Extensive docstrings and examples

---

## Why This Library?

### The Two-API Problem

TickTick has **two different APIs**:

| API | Type | What We Use It For |
|-----|------|-------------------|
| **V1 (OAuth2)** | Official, documented | Project with all tasks, basic operations |
| **V2 (Session)** | Unofficial, reverse-engineered | Tags, folders, habits, focus, subtasks, and more |

The official V1 API is limited. Most of TickTick's power features (tags, habits, focus tracking) are only available through the undocumented V2 web API. **This library combines both**, routing each operation to the appropriate API automatically.

### Compared to Other Libraries

Based on analysis of the actual source code of available TickTick Python libraries:

| Feature | ticktick-sdk | [pyticktick](https://github.com/sebpretzer/pyticktick) | [ticktick-py](https://github.com/lazeroffmichael/ticktick-py) | [tickthon](https://github.com/anggelomos/tickthon) | [ticktick-python](https://github.com/glasslion/ticktick-python) |
|---------|:------------:|:----------:|:-----------:|:--------:|:---------------:|
| **I/O Model** | Async | Async | Sync | Sync | Sync |
| **Type System** | Pydantic V2 | Pydantic V2 | Dicts | attrs | addict |
| **MCP Server** | **Yes** | No | No | No | No |
| **Habits** | **Full CRUD** | No | Basic | Basic | No |
| **Focus/Pomo** | Yes | Yes | Yes | Yes | No |
| **Unified V1+V2** | **Smart Routing** | Separate | Both | V2 only | V2 only |
| **Subtasks** | Advanced | Batch | Yes | Basic | Basic |
| **Tags** | Full (merge/rename) | Yes | Yes | Yes | No |

**Key Differentiators:**

- **MCP Server**: Only ticktick-sdk provides AI assistant integration via Model Context Protocol
- **Unified API Routing**: Automatically routes operations to V1 or V2 based on feature requirements
- **Full Habit CRUD**: Complete habit management including check-ins, streaks, archive/unarchive
- **Async-First**: Built on `httpx` for high-performance async operations

---

## Installation

```bash
pip install ticktick-sdk
```

**Requirements:**
- Python 3.11+
- TickTick account (free or Pro)

---

## MCP Server Setup & Usage

Use TickTick with AI assistants like Claude through the Model Context Protocol.

### Step 1: Register Your App

1. Go to the [TickTick Developer Portal](https://developer.ticktick.com/manage)
2. Click **"Create App"**
3. Fill in:
   - **App Name**: e.g., "My TickTick MCP"
   - **Redirect URI**: `http://127.0.0.1:8080/callback`
4. Save your **Client ID** and **Client Secret**

### Step 2: Get OAuth2 Access Token

Run the auth command with your credentials:

```bash
TICKTICK_CLIENT_ID=your_client_id \
TICKTICK_CLIENT_SECRET=your_client_secret \
ticktick-sdk auth
```

This will:
1. **Open your browser** to TickTick's authorization page
2. **Authorize the app** - Click "Authorize" to grant access
3. **Return to terminal** - After authorizing, you'll see output like this:

```
============================================================
  SUCCESS! Here is your access token:
============================================================

a]234abc-5678-90de-f012-34567890abcd

============================================================

NEXT STEPS:

For Claude Code users:
  Run (replace YOUR_* placeholders):
    claude mcp add ticktick \
      -e TICKTICK_CLIENT_ID=YOUR_CLIENT_ID \
      ...
```

4. **Copy this token** - You'll need it in the next step

> **Note**: Sometimes the browser shows an "invalid credentials" error page. Just refresh the page and it should work.

> **SSH/Headless Users**: Add `--manual` flag for a text-based flow that doesn't require a browser.

### Step 3: Configure Your AI Assistant

#### Claude Code (Recommended)

```bash
claude mcp add ticktick \
  -e TICKTICK_CLIENT_ID=your_client_id \
  -e TICKTICK_CLIENT_SECRET=your_client_secret \
  -e TICKTICK_ACCESS_TOKEN=your_access_token \
  -e TICKTICK_USERNAME=your_email \
  -e TICKTICK_PASSWORD=your_password \
  -- ticktick-sdk
```

> **Note**: For `TICKTICK_ACCESS_TOKEN`, paste the token you copied from Step 2.

Verify it's working:

```bash
claude mcp list        # See all configured servers
/mcp                   # Within Claude Code, check server status
```

#### Claude Desktop

Add to your Claude Desktop config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ticktick": {
      "command": "ticktick-sdk",
      "env": {
        "TICKTICK_CLIENT_ID": "your_client_id",
        "TICKTICK_CLIENT_SECRET": "your_client_secret",
        "TICKTICK_ACCESS_TOKEN": "your_access_token",
        "TICKTICK_USERNAME": "your_email",
        "TICKTICK_PASSWORD": "your_password"
      }
    }
  }
}
```

#### Other MCP-Compatible Tools

This server works with any tool that supports the Model Context Protocol, which includes most modern AI assistants and IDEs. The configuration is similar - you just need to provide the command (`ticktick-sdk`) and the environment variables shown above.

### CLI Reference

The `ticktick-sdk` command provides several subcommands:

| Command | Description |
|---------|-------------|
| `ticktick-sdk` | Start the MCP server (default) |
| `ticktick-sdk server` | Start the MCP server (explicit) |
| `ticktick-sdk auth` | Get OAuth2 access token (opens browser) |
| `ticktick-sdk auth --manual` | Get OAuth2 access token (SSH-friendly) |
| `ticktick-sdk --version` | Show version information |
| `ticktick-sdk --help` | Show help message |

### Example Conversations

Once configured, you can ask Claude things like:

- "What tasks do I have due today?"
- "Create a task to call John tomorrow at 2pm"
- "Show me my high priority tasks"
- "Mark the grocery shopping task as complete"
- "What's my current streak for the Exercise habit?"
- "Check in my meditation habit for today"
- "Create a new habit to drink 8 glasses of water daily"

### Available MCP Tools (45 Total)

#### Task Tools
| Tool | Description |
|------|-------------|
| `ticktick_create_task` | Create a new task with title, dates, tags, etc. |
| `ticktick_get_task` | Get task details by ID |
| `ticktick_list_tasks` | List tasks with optional filters |
| `ticktick_update_task` | Update task properties |
| `ticktick_complete_task` | Mark task as complete |
| `ticktick_delete_task` | Delete a task (moves to trash) |
| `ticktick_move_task` | Move task between projects |
| `ticktick_make_subtask` | Create parent-child relationship |
| `ticktick_unparent_subtask` | Remove parent-child relationship |
| `ticktick_completed_tasks` | List recently completed tasks |
| `ticktick_abandoned_tasks` | List abandoned ("won't do") tasks |
| `ticktick_deleted_tasks` | List deleted tasks (in trash) |
| `ticktick_search_tasks` | Search tasks by text |

#### Project Tools
| Tool | Description |
|------|-------------|
| `ticktick_list_projects` | List all projects |
| `ticktick_get_project` | Get project details with tasks |
| `ticktick_create_project` | Create a new project |
| `ticktick_update_project` | Update project properties |
| `ticktick_delete_project` | Delete a project |

#### Folder Tools
| Tool | Description |
|------|-------------|
| `ticktick_list_folders` | List all folders |
| `ticktick_create_folder` | Create a folder |
| `ticktick_rename_folder` | Rename a folder |
| `ticktick_delete_folder` | Delete a folder |

#### Tag Tools
| Tool | Description |
|------|-------------|
| `ticktick_list_tags` | List all tags |
| `ticktick_create_tag` | Create a tag with color |
| `ticktick_update_tag` | Update tag color/parent |
| `ticktick_delete_tag` | Delete a tag |
| `ticktick_rename_tag` | Rename a tag |
| `ticktick_merge_tags` | Merge two tags |

#### Habit Tools
| Tool | Description |
|------|-------------|
| `ticktick_habits` | List all habits |
| `ticktick_habit` | Get habit details |
| `ticktick_habit_sections` | List sections (morning/afternoon/night) |
| `ticktick_create_habit` | Create a new habit |
| `ticktick_update_habit` | Update habit properties |
| `ticktick_delete_habit` | Delete a habit |
| `ticktick_checkin_habit` | Check in for today or a past date |
| `ticktick_archive_habit` | Archive a habit |
| `ticktick_unarchive_habit` | Unarchive a habit |
| `ticktick_habit_checkins` | Get check-in history |

#### User & Analytics Tools
| Tool | Description |
|------|-------------|
| `ticktick_get_profile` | Get user profile |
| `ticktick_get_status` | Get account status |
| `ticktick_get_statistics` | Get productivity stats |
| `ticktick_get_preferences` | Get user preferences |
| `ticktick_focus_heatmap` | Get focus heatmap data |
| `ticktick_focus_by_tag` | Get focus time by tag |

---

## Python Library Setup & Usage

Use TickTick programmatically in your Python applications.

### Setup

#### Step 1: Register Your App

Same as MCP setup - go to the [TickTick Developer Portal](https://developer.ticktick.com/manage) and create an app.

#### Step 2: Create Your .env File

Create a `.env` file in your project directory:

```bash
# V1 API (OAuth2)
TICKTICK_CLIENT_ID=your_client_id_here
TICKTICK_CLIENT_SECRET=your_client_secret_here
TICKTICK_REDIRECT_URI=http://127.0.0.1:8080/callback
TICKTICK_ACCESS_TOKEN=  # Will be filled in Step 3

# V2 API (Session)
TICKTICK_USERNAME=your_ticktick_email@example.com
TICKTICK_PASSWORD=your_ticktick_password

# Optional
TICKTICK_TIMEOUT=30
```

#### Step 3: Get OAuth2 Access Token

```bash
# Source your .env file first, or export the variables
ticktick-sdk auth
```

Copy the access token to your `.env` file.

#### Step 4: Verify Setup

```python
import asyncio
from ticktick_sdk import TickTickClient

async def test():
    async with TickTickClient.from_settings() as client:
        profile = await client.get_profile()
        print(f'Connected as: {profile.display_name}')

asyncio.run(test())
```

### Quick Start

```python
import asyncio
from ticktick_sdk import TickTickClient

async def main():
    async with TickTickClient.from_settings() as client:
        # Create a task
        task = await client.create_task(
            title="Learn ticktick-sdk",
            tags=["python", "productivity"],
        )
        print(f"Created: {task.title} (ID: {task.id})")

        # List all tasks
        tasks = await client.get_all_tasks()
        print(f"You have {len(tasks)} active tasks")

        # Complete the task
        await client.complete_task(task.id, task.project_id)
        print("Task completed!")

asyncio.run(main())
```

### Tasks

#### Creating Tasks

```python
from datetime import datetime, timedelta
from ticktick_sdk import TickTickClient

async with TickTickClient.from_settings() as client:
    # Simple task
    task = await client.create_task(title="Buy groceries")

    # Task with due date and priority
    task = await client.create_task(
        title="Submit report",
        due_date=datetime.now() + timedelta(days=1),
        priority="high",  # none, low, medium, high
    )

    # Task with tags and content
    task = await client.create_task(
        title="Review PR #123",
        content="Check for:\n- Code style\n- Tests\n- Documentation",
        tags=["work", "code-review"],
    )

    # Recurring task (MUST include start_date!)
    task = await client.create_task(
        title="Daily standup",
        start_date=datetime(2025, 1, 20, 9, 0),
        recurrence="RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR",
    )

    # Task with reminder
    task = await client.create_task(
        title="Meeting with team",
        due_date=datetime(2025, 1, 20, 14, 0),
        reminders=["TRIGGER:-PT15M"],  # 15 minutes before
    )

    # All-day task
    task = await client.create_task(
        title="Project deadline",
        due_date=datetime(2025, 1, 31),
        all_day=True,
    )
```

#### Managing Tasks

```python
async with TickTickClient.from_settings() as client:
    # Get a specific task
    task = await client.get_task(task_id="...")

    # Update a task
    task.title = "Updated title"
    task.priority = 5  # high priority
    await client.update_task(task)

    # Complete a task
    await client.complete_task(task_id="...", project_id="...")

    # Delete a task (moves to trash)
    await client.delete_task(task_id="...", project_id="...")

    # Move task to another project
    await client.move_task(
        task_id="...",
        from_project_id="...",
        to_project_id="...",
    )
```

#### Subtasks

```python
async with TickTickClient.from_settings() as client:
    # Create parent task
    parent = await client.create_task(title="Main task")

    # Create child task
    child = await client.create_task(title="Subtask")

    # Make it a subtask (parent_id in create is ignored by API)
    await client.make_subtask(
        task_id=child.id,
        parent_id=parent.id,
        project_id=child.project_id,
    )

    # Remove parent relationship
    await client.unparent_subtask(
        task_id=child.id,
        project_id=child.project_id,
    )
```

#### Querying Tasks

```python
async with TickTickClient.from_settings() as client:
    # All active tasks
    all_tasks = await client.get_all_tasks()

    # Tasks due today
    today = await client.get_today_tasks()

    # Overdue tasks
    overdue = await client.get_overdue_tasks()

    # Tasks by tag
    work_tasks = await client.get_tasks_by_tag("work")

    # Tasks by priority
    urgent = await client.get_tasks_by_priority("high")

    # Search tasks
    results = await client.search_tasks("meeting")

    # Recently completed
    completed = await client.get_completed_tasks(days=7, limit=50)

    # Abandoned tasks ("won't do")
    abandoned = await client.get_abandoned_tasks(days=30)

    # Deleted tasks (in trash)
    deleted = await client.get_deleted_tasks(limit=50)
```

### Projects & Folders

#### Projects

```python
async with TickTickClient.from_settings() as client:
    # List all projects
    projects = await client.get_all_projects()
    for project in projects:
        print(f"{project.name} ({project.id})")

    # Get project with all its tasks
    project_data = await client.get_project_tasks(project_id="...")
    print(f"Project: {project_data.project.name}")
    print(f"Tasks: {len(project_data.tasks)}")

    # Create a project
    project = await client.create_project(
        name="Q1 Goals",
        color="#4A90D9",
        view_mode="kanban",  # list, kanban, timeline
    )

    # Update a project
    await client.update_project(
        project_id=project.id,
        name="Q1 Goals 2025",
        color="#FF5500",
    )

    # Delete a project
    await client.delete_project(project_id="...")
```

#### Folders (Project Groups)

```python
async with TickTickClient.from_settings() as client:
    # List all folders
    folders = await client.get_all_folders()

    # Create a folder
    folder = await client.create_folder(name="Work Projects")

    # Create project in folder
    project = await client.create_project(
        name="Client A",
        folder_id=folder.id,
    )

    # Rename a folder
    await client.rename_folder(folder_id=folder.id, name="Work")

    # Delete a folder
    await client.delete_folder(folder_id="...")
```

### Tags

Tags in TickTick support hierarchy (parent-child relationships) and custom colors.

```python
async with TickTickClient.from_settings() as client:
    # List all tags
    tags = await client.get_all_tags()
    for tag in tags:
        print(f"{tag.label} ({tag.name}) - {tag.color}")

    # Create a tag
    tag = await client.create_tag(
        name="urgent",
        color="#FF0000",
    )

    # Create nested tag
    child_tag = await client.create_tag(
        name="critical",
        parent="urgent",  # Parent tag name
    )

    # Rename a tag
    await client.rename_tag(old_name="urgent", new_name="priority")

    # Update tag color or parent
    await client.update_tag(
        name="priority",
        color="#FF5500",
    )

    # Merge tags (move all tasks from source to target)
    await client.merge_tags(source="old-tag", target="new-tag")

    # Delete a tag
    await client.delete_tag(name="obsolete")
```

### Habits

TickTick habits are recurring activities you want to track daily.

#### Habit Types

| Type | Description | Example |
|------|-------------|---------|
| `Boolean` | Simple yes/no | "Did you exercise today?" |
| `Real` | Numeric counter | "How many pages did you read?" |

#### Creating and Managing Habits

```python
async with TickTickClient.from_settings() as client:
    # List all habits
    habits = await client.get_all_habits()

    # Boolean habit (yes/no)
    exercise = await client.create_habit(
        name="Exercise",
        color="#4A90D9",
        reminders=["07:00", "19:00"],
        target_days=30,
        encouragement="Stay strong!",
    )

    # Numeric habit
    reading = await client.create_habit(
        name="Read",
        habit_type="Real",
        goal=30,           # 30 pages per day
        step=5,            # +5 button increment
        unit="Pages",
    )

    # Check in a habit (today)
    habit = await client.checkin_habit("habit_id")
    print(f"Streak: {habit.current_streak} days!")

    # Check in for a past date (backdate)
    from datetime import date
    habit = await client.checkin_habit("habit_id", checkin_date=date(2025, 12, 15))

    # Archive/unarchive
    await client.archive_habit("habit_id")
    await client.unarchive_habit("habit_id")
```

#### Habit Repeat Rules (RRULE Format)

| Schedule | RRULE |
|----------|-------|
| Daily (every day) | `RRULE:FREQ=WEEKLY;BYDAY=SU,MO,TU,WE,TH,FR,SA` |
| Weekdays only | `RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR` |
| Weekends only | `RRULE:FREQ=WEEKLY;BYDAY=SA,SU` |
| X times per week | `RRULE:FREQ=WEEKLY;TT_TIMES=5` |
| Specific days | `RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR` |

### Focus/Pomodoro

```python
from datetime import date, timedelta

async with TickTickClient.from_settings() as client:
    # Focus heatmap (like GitHub contribution graph)
    heatmap = await client.get_focus_heatmap(
        start_date=date.today() - timedelta(days=90),
        end_date=date.today(),
    )

    # Focus time by tag
    by_tag = await client.get_focus_by_tag(days=30)
    for tag, seconds in sorted(by_tag.items(), key=lambda x: -x[1]):
        hours = seconds / 3600
        print(f"  {tag}: {hours:.1f} hours")
```

### User & Statistics

```python
async with TickTickClient.from_settings() as client:
    # User profile
    profile = await client.get_profile()
    print(f"Username: {profile.username}")

    # Account status
    status = await client.get_status()
    print(f"Pro User: {status.is_pro}")
    print(f"Inbox ID: {status.inbox_id}")

    # Productivity statistics
    stats = await client.get_statistics()
    print(f"Level: {stats.level}")
    print(f"Score: {stats.score}")
    print(f"Tasks completed today: {stats.today_completed}")
```

### Error Handling

```python
from ticktick_sdk import (
    TickTickClient,
    TickTickError,
    TickTickNotFoundError,
    TickTickAuthenticationError,
    TickTickRateLimitError,
    TickTickValidationError,
)

async with TickTickClient.from_settings() as client:
    try:
        task = await client.get_task("nonexistent-id")
    except TickTickNotFoundError as e:
        print(f"Task not found: {e}")
    except TickTickAuthenticationError:
        print("Authentication failed - check credentials")
    except TickTickRateLimitError:
        print("Rate limited - wait and retry")
    except TickTickValidationError as e:
        print(f"Invalid input: {e}")
    except TickTickError as e:
        print(f"TickTick error: {e}")
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                         │
│              (or MCP Server for AI Assistants)              │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    TickTickClient                           │
│            High-level, user-friendly async API              │
│   (tasks, projects, tags, habits, focus, user methods)      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  UnifiedTickTickAPI                         │
│        Routes calls to V1 or V2, converts responses         │
│              to unified Pydantic models                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
┌──────────────────────┐      ┌──────────────────────┐
│      V1 API          │      │      V2 API          │
│     (OAuth2)         │      │     (Session)        │
│                      │      │                      │
│ • Official API       │      │ • Unofficial API     │
│ • Project with tasks │      │ • Tags, folders      │
│ • Limited features   │      │ • Habits, focus      │
│                      │      │ • Full subtasks      │
└──────────────────────┘      └──────────────────────┘
```

### Key Design Decisions

1. **V2-First**: Most operations use V2 API (more features), falling back to V1 only when needed
2. **Unified Models**: Single set of Pydantic models regardless of which API provides the data
3. **Async Throughout**: All I/O operations are async for performance
4. **Type Safety**: Full type hints and Pydantic validation

---

## API Reference

### Models

| Model | Description |
|-------|-------------|
| `Task` | Task with title, dates, priority, tags, subtasks, recurrence, etc. |
| `Project` | Project/list container for tasks |
| `ProjectGroup` | Folder for organizing projects |
| `ProjectData` | Project with its tasks (from get_project_tasks) |
| `Tag` | Tag with name, label, color, and optional parent |
| `Habit` | Recurring habit with type, goals, streaks, and check-ins |
| `HabitSection` | Time-of-day grouping (morning/afternoon/night) |
| `HabitCheckin` | Individual habit check-in record |
| `HabitPreferences` | User habit settings |
| `User` | User profile information |
| `UserStatus` | Account status (Pro, inbox ID, etc.) |
| `UserStatistics` | Productivity statistics (level, score, counts) |
| `ChecklistItem` | Subtask/checklist item within a task |

### Enums

| Enum | Values |
|------|--------|
| `TaskStatus` | `ABANDONED (-1)`, `ACTIVE (0)`, `COMPLETED (2)` |
| `TaskPriority` | `NONE (0)`, `LOW (1)`, `MEDIUM (3)`, `HIGH (5)` |
| `TaskKind` | `TEXT`, `NOTE`, `CHECKLIST` |
| `ProjectKind` | `TASK`, `NOTE` |
| `ViewMode` | `LIST`, `KANBAN`, `TIMELINE` |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `TickTickError` | Base exception for all errors |
| `TickTickAuthenticationError` | Authentication failed |
| `TickTickNotFoundError` | Resource not found |
| `TickTickValidationError` | Invalid input data |
| `TickTickRateLimitError` | Rate limit exceeded |
| `TickTickConfigurationError` | Missing configuration |
| `TickTickForbiddenError` | Access denied |
| `TickTickServerError` | Server-side error |

---

## Important: TickTick API Quirks

TickTick's API has several unique behaviors you should know about:

### 1. Recurrence Requires start_date

**If you create a recurring task without a start_date, TickTick silently ignores the recurrence rule.**

```python
# WRONG - recurrence will be ignored!
task = await client.create_task(
    title="Daily standup",
    recurrence="RRULE:FREQ=DAILY",
)

# CORRECT
task = await client.create_task(
    title="Daily standup",
    start_date=datetime(2025, 1, 20, 9, 0),
    recurrence="RRULE:FREQ=DAILY",
)
```

### 2. Subtasks Require Separate Call

Setting `parent_id` during task creation is **ignored** by the API:

```python
# Create the child task first
child = await client.create_task(title="Subtask")

# Then make it a subtask
await client.make_subtask(
    task_id=child.id,
    parent_id="parent_task_id",
    project_id=child.project_id,
)
```

### 3. Soft Delete

Deleting tasks moves them to trash (`deleted=1`) rather than permanently removing them.

### 4. Date Clearing

To clear a task's `due_date`, you must also clear `start_date`:

```python
task.due_date = None
task.start_date = None
await client.update_task(task)
```

### 5. Tag Order Not Preserved

The API does not preserve tag order - tags may be returned in any order.

### 6. Inbox is Special

The inbox is a special project that cannot be deleted. Get its ID via `await client.get_status()`.

---

## Environment Variables

| Variable | Required | Description |
|----------|:--------:|-------------|
| `TICKTICK_CLIENT_ID` | Yes | OAuth2 client ID from developer portal |
| `TICKTICK_CLIENT_SECRET` | Yes | OAuth2 client secret |
| `TICKTICK_ACCESS_TOKEN` | Yes | OAuth2 access token (from auth command) |
| `TICKTICK_USERNAME` | Yes | Your TickTick email |
| `TICKTICK_PASSWORD` | Yes | Your TickTick password |
| `TICKTICK_REDIRECT_URI` | No | OAuth2 redirect URI (default: `http://127.0.0.1:8080/callback`) |
| `TICKTICK_TIMEOUT` | No | Request timeout in seconds (default: `30`) |
| `TICKTICK_DEVICE_ID` | No | Device ID for V2 API (auto-generated) |

---

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# All tests (mock mode - no API calls)
pytest

# With verbose output
pytest -v

# Live tests (requires credentials)
pytest --live

# With coverage
pytest --cov=ticktick_sdk --cov-report=term-missing
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `unit` | Unit tests (fast, isolated) |
| `tasks` | Task-related tests |
| `projects` | Project-related tests |
| `tags` | Tag-related tests |
| `habits` | Habit-related tests |
| `focus` | Focus/Pomodoro tests |
| `mock_only` | Tests that only work with mocks |
| `live_only` | Tests that only run with `--live` |

---

## Troubleshooting

### "Token exchange failed"
- Verify your Client ID and Client Secret are correct
- Ensure the Redirect URI matches exactly (including trailing slashes)
- Check that you're using the correct TickTick developer portal

### "Authentication failed"
- Check your TickTick username (email) and password
- Try logging into ticktick.com to verify credentials

### "V2 initialization failed"
- Your password may contain special characters - try changing it
- Check for 2FA/MFA (not currently supported)

### "Rate limit exceeded"
- Wait 30-60 seconds before retrying
- Reduce the frequency of API calls

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Run type checking (`mypy src/`)
6. Submit a pull request

### Development Setup

```bash
git clone https://github.com/dev-mirzabicer/ticktick-sdk.git
cd ticktick-sdk
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [TickTick](https://ticktick.com) for the excellent task management app
- [Model Context Protocol](https://modelcontextprotocol.io/) for the AI integration standard
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP framework
- [Pydantic](https://docs.pydantic.dev/) for data validation
- [httpx](https://www.python-httpx.org/) for async HTTP

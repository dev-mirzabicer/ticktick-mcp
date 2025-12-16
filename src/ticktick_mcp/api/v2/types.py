"""
Type definitions for TickTick V2 API.

These TypedDicts represent the JSON structures used in V2 API
requests and responses. V2 has significantly richer data models than V1.
"""

from __future__ import annotations

from typing import Any, TypedDict, NotRequired


# =============================================================================
# Focus & Pomodoro
# =============================================================================


class FocusSummaryV2(TypedDict):
    """Focus/Pomodoro summary data."""

    userId: int
    pomoCount: NotRequired[int]
    estimatedPomo: NotRequired[int]
    estimatedDuration: NotRequired[int]
    pomoDuration: NotRequired[int]
    stopwatchDuration: NotRequired[int]
    focuses: NotRequired[list[Any]]  # [?, ?, duration_seconds]


class PomodoroSummaryV2(TypedDict):
    """Pomodoro summary data."""

    userId: int
    count: NotRequired[int]
    estimatedPomo: NotRequired[int]
    duration: NotRequired[int]


# =============================================================================
# Reminder
# =============================================================================


class TaskReminderV2(TypedDict):
    """V2 API task reminder."""

    id: NotRequired[str]
    trigger: str  # ICalTrigger format


# =============================================================================
# Checklist Item (Subtask)
# =============================================================================


class ItemV2(TypedDict):
    """V2 API checklist/subtask item."""

    id: str
    title: NotRequired[str]
    status: NotRequired[int]  # -1, 0, 1, 2
    completedTime: NotRequired[str]
    startDate: NotRequired[str]
    timeZone: NotRequired[str]
    isAllDay: NotRequired[bool]
    sortOrder: NotRequired[int]
    snoozeReminderTime: NotRequired[Any]


# =============================================================================
# Task
# =============================================================================


class TaskV2(TypedDict):
    """V2 API task response."""

    # Core identifiers
    id: str
    projectId: str
    etag: NotRequired[str]

    # Content
    title: NotRequired[str]
    content: NotRequired[str]
    desc: NotRequired[str]
    kind: NotRequired[str]  # TEXT, NOTE, CHECKLIST

    # Status
    status: NotRequired[int]  # -1, 0, 1, 2
    priority: NotRequired[int]  # 0, 1, 3, 5
    progress: NotRequired[int]  # 0-100
    deleted: NotRequired[int]  # 0 or 1

    # Dates
    startDate: NotRequired[str]
    dueDate: NotRequired[str]
    createdTime: NotRequired[str]
    modifiedTime: NotRequired[str]
    completedTime: NotRequired[str]
    timeZone: NotRequired[str]
    isAllDay: NotRequired[bool]
    isFloating: NotRequired[bool]

    # Recurrence
    repeatFlag: NotRequired[str]
    repeatFrom: NotRequired[int]  # 0, 1, 2
    repeatFirstDate: NotRequired[str]
    repeatTaskId: NotRequired[str]
    exDate: NotRequired[list[str]]

    # Reminders
    reminder: NotRequired[str]
    reminders: NotRequired[list[TaskReminderV2]]
    remindTime: NotRequired[str]
    annoyingAlert: NotRequired[int]

    # Hierarchy
    parentId: NotRequired[str]
    childIds: NotRequired[list[str]]

    # Checklist items
    items: NotRequired[list[ItemV2]]

    # Organization
    tags: NotRequired[list[str]]
    columnId: NotRequired[str]
    sortOrder: NotRequired[int]

    # Collaboration
    assignee: NotRequired[Any]
    creator: NotRequired[int]
    completedUserId: NotRequired[int]
    commentCount: NotRequired[int]

    # Attachments
    attachments: NotRequired[list[Any]]

    # Focus
    focusSummaries: NotRequired[list[FocusSummaryV2]]
    pomodoroSummaries: NotRequired[list[PomodoroSummaryV2]]

    # Other
    imgMode: NotRequired[int]
    isDirty: NotRequired[bool]
    local: NotRequired[bool]


class TaskCreateV2(TypedDict, total=False):
    """V2 API task creation request."""

    title: str
    projectId: str
    content: str
    desc: str
    kind: str
    priority: int
    startDate: str
    dueDate: str
    timeZone: str
    isAllDay: bool
    reminders: list[TaskReminderV2]
    repeatFlag: str
    tags: list[str]
    items: list[ItemV2]
    sortOrder: int
    parentId: str


class TaskUpdateV2(TypedDict, total=False):
    """V2 API task update request."""

    id: str  # Required
    projectId: str  # Required
    title: str
    content: str
    desc: str
    kind: str
    status: int
    priority: int
    startDate: str
    dueDate: str
    timeZone: str
    isAllDay: bool
    reminders: list[TaskReminderV2]
    repeatFlag: str
    tags: list[str]
    items: list[ItemV2]
    sortOrder: int
    completedTime: str


class TaskDeleteV2(TypedDict):
    """V2 API task deletion request."""

    projectId: str
    taskId: str


class TaskMoveV2(TypedDict):
    """V2 API task move request."""

    fromProjectId: str
    toProjectId: str
    taskId: str


class TaskParentV2(TypedDict, total=False):
    """V2 API task parent modification request."""

    taskId: str
    projectId: str
    parentId: str  # Set to make subtask
    oldParentId: str  # Set to unset parent


# =============================================================================
# Project
# =============================================================================


class SortOptionV2(TypedDict, total=False):
    """Sorting options."""

    groupBy: str
    orderBy: str


class ProjectTimelineV2(TypedDict, total=False):
    """Timeline settings."""

    range: str
    sortType: str
    sortOption: SortOptionV2


class ProjectV2(TypedDict):
    """V2 API project response."""

    # Core
    id: str
    etag: NotRequired[str]
    name: str
    color: NotRequired[str]
    kind: NotRequired[str]  # TASK, NOTE

    # Organization
    groupId: NotRequired[str]
    inAll: NotRequired[bool]
    viewMode: NotRequired[str]  # list, kanban, timeline
    sortOption: NotRequired[SortOptionV2]
    sortOrder: NotRequired[int]
    sortType: NotRequired[str]

    # Metadata
    modifiedTime: NotRequired[str]
    isOwner: NotRequired[bool]
    userCount: NotRequired[int]

    # Status
    closed: NotRequired[Any]
    muted: NotRequired[bool]
    transferred: NotRequired[Any]

    # Team/Sharing
    teamId: NotRequired[Any]
    permission: NotRequired[Any]
    notificationOptions: NotRequired[Any]
    openToTeam: NotRequired[bool]
    teamMemberPermission: NotRequired[Any]

    # Other
    background: NotRequired[Any]
    barcodeNeedAudit: NotRequired[bool]
    needAudit: NotRequired[bool]
    timeline: NotRequired[ProjectTimelineV2]
    source: NotRequired[int]
    showType: NotRequired[int]
    reminderType: NotRequired[int]


class ProjectCreateV2(TypedDict, total=False):
    """V2 API project creation request."""

    name: str
    id: str  # Optional client-generated ID
    color: str
    kind: str
    viewMode: str
    groupId: str
    sortOrder: int


class ProjectUpdateV2(TypedDict, total=False):
    """V2 API project update request."""

    id: str  # Required
    name: str  # Required
    color: str
    groupId: str  # Use "NONE" to ungroup


# =============================================================================
# Project Group (Folder)
# =============================================================================


class ProjectGroupV2(TypedDict):
    """V2 API project group/folder response."""

    id: str
    etag: NotRequired[str]
    name: str

    # Display
    viewMode: NotRequired[str]
    sortOption: NotRequired[SortOptionV2]
    sortOrder: NotRequired[int]
    sortType: NotRequired[str]

    # Status
    deleted: NotRequired[int]
    showAll: NotRequired[bool]

    # Team
    teamId: NotRequired[Any]
    userId: NotRequired[int]

    # Other
    background: NotRequired[Any]
    timeline: NotRequired[ProjectTimelineV2]


class ProjectGroupCreateV2(TypedDict, total=False):
    """V2 API project group creation request."""

    name: str
    listType: str  # Always "group"


class ProjectGroupUpdateV2(TypedDict, total=False):
    """V2 API project group update request."""

    id: str  # Required
    name: str  # Required
    listType: str  # Always "group"


# =============================================================================
# Tag
# =============================================================================


class TagV2(TypedDict):
    """V2 API tag response."""

    name: str  # Lowercase identifier
    label: str  # Display name
    rawName: NotRequired[str]
    etag: NotRequired[str]

    # Appearance
    color: NotRequired[str]

    # Hierarchy
    parent: NotRequired[str]

    # Sorting
    sortOption: NotRequired[SortOptionV2]
    sortType: NotRequired[str]
    sortOrder: NotRequired[int]

    # Other
    timeline: NotRequired[ProjectTimelineV2]
    type: NotRequired[int]


class TagCreateV2(TypedDict, total=False):
    """V2 API tag creation request."""

    label: str  # Required
    name: str
    color: str
    parent: str
    sortType: str
    sortOrder: int


class TagUpdateV2(TypedDict, total=False):
    """V2 API tag update request."""

    label: str  # Required
    name: str  # Required
    rawName: str
    color: str
    parent: str
    sortType: str
    sortOrder: int


class TagRenameV2(TypedDict):
    """V2 API tag rename request."""

    name: str  # Old name
    newName: str  # New label


class TagMergeV2(TypedDict):
    """V2 API tag merge request."""

    name: str  # Source tag
    newName: str  # Target tag


# =============================================================================
# Sync Response
# =============================================================================


class SyncTaskBeanV2(TypedDict):
    """Sync task data."""

    update: list[TaskV2]
    add: NotRequired[list[TaskV2]]
    delete: NotRequired[list[Any]]
    empty: NotRequired[bool]
    tagUpdate: NotRequired[list[Any]]


class SyncStateV2(TypedDict):
    """V2 API sync state response (batch/check/0)."""

    inboxId: str
    projectProfiles: list[ProjectV2]
    projectGroups: list[ProjectGroupV2]
    syncTaskBean: SyncTaskBeanV2
    tags: list[TagV2]
    filters: NotRequired[list[Any]]
    checkPoint: int
    checks: NotRequired[Any]
    syncOrderBean: NotRequired[Any]
    syncOrderBeanV3: NotRequired[Any]
    syncTaskOrderBean: NotRequired[Any]
    remindChanges: NotRequired[list[Any]]


# =============================================================================
# Batch Operations
# =============================================================================


class BatchTaskRequestV2(TypedDict, total=False):
    """V2 API batch task request."""

    add: list[TaskCreateV2]
    update: list[TaskUpdateV2]
    delete: list[TaskDeleteV2]
    addAttachments: list[Any]
    updateAttachments: list[Any]
    deleteAttachments: list[Any]


class BatchProjectRequestV2(TypedDict, total=False):
    """V2 API batch project request."""

    add: list[ProjectCreateV2]
    update: list[ProjectUpdateV2]
    delete: list[str]


class BatchProjectGroupRequestV2(TypedDict, total=False):
    """V2 API batch project group request."""

    add: list[ProjectGroupCreateV2]
    update: list[ProjectGroupUpdateV2]
    delete: list[str]


class BatchTagRequestV2(TypedDict, total=False):
    """V2 API batch tag request."""

    add: list[TagCreateV2]
    update: list[TagUpdateV2]


class BatchResponseV2(TypedDict):
    """V2 API batch response."""

    id2etag: dict[str, str]
    id2error: dict[str, str]


class BatchTaskParentResponseV2(TypedDict):
    """V2 API batch task parent response."""

    id2etag: dict[str, dict[str, Any]]
    id2error: dict[str, str]


# =============================================================================
# User
# =============================================================================


class UserStatusV2(TypedDict):
    """V2 API user status response."""

    userId: str
    userCode: NotRequired[str]
    username: str
    teamPro: NotRequired[bool]
    proStartDate: NotRequired[str]
    proEndDate: NotRequired[str]
    subscribeType: NotRequired[str]
    subscribeFreq: NotRequired[str]
    needSubscribe: NotRequired[bool]
    freq: NotRequired[str]
    inboxId: str
    teamUser: NotRequired[bool]
    activeTeamUser: NotRequired[bool]
    freeTrial: NotRequired[bool]
    pro: NotRequired[bool]
    ds: NotRequired[bool]
    timeStamp: NotRequired[int]
    gracePeriod: NotRequired[bool]


class UserProfileV2(TypedDict):
    """V2 API user profile response."""

    username: str
    displayName: NotRequired[str]
    name: NotRequired[str]
    picture: NotRequired[str]
    locale: NotRequired[str]
    siteDomain: NotRequired[str]
    userCode: NotRequired[str]
    verifiedEmail: NotRequired[bool]
    filledPassword: NotRequired[bool]
    fakedEmail: NotRequired[bool]
    etimestamp: NotRequired[Any]
    createdCampaign: NotRequired[str]
    createdDeviceInfo: NotRequired[Any]
    accountDomain: NotRequired[Any]
    email: NotRequired[str]


class UserPreferencesV2(TypedDict):
    """V2 API user preferences response."""

    id: str
    timeZone: NotRequired[str]


# =============================================================================
# Statistics
# =============================================================================


class TaskCountV2(TypedDict):
    """Task count data."""

    completeCount: int
    notCompleteCount: int


class UserStatisticsV2(TypedDict):
    """V2 API user statistics response."""

    score: NotRequired[int]
    level: NotRequired[int]
    yesterdayCompleted: NotRequired[int]
    todayCompleted: NotRequired[int]
    totalCompleted: NotRequired[int]
    scoreByDay: NotRequired[dict[str, int]]
    taskByDay: NotRequired[dict[str, TaskCountV2]]
    taskByWeek: NotRequired[dict[str, TaskCountV2]]
    taskByMonth: NotRequired[dict[str, TaskCountV2]]
    todayPomoCount: NotRequired[int]
    yesterdayPomoCount: NotRequired[int]
    totalPomoCount: NotRequired[int]
    todayPomoDuration: NotRequired[int]
    yesterdayPomoDuration: NotRequired[int]
    totalPomoDuration: NotRequired[int]
    pomoGoal: NotRequired[int]
    pomoDurationGoal: NotRequired[int]
    pomoByDay: NotRequired[dict[str, Any]]
    pomoByWeek: NotRequired[dict[str, Any]]
    pomoByMonth: NotRequired[dict[str, Any]]


# =============================================================================
# Focus/Pomodoro Statistics
# =============================================================================


class FocusHeatmapV2(TypedDict):
    """Focus heatmap data point."""

    duration: int


class FocusDistributionV2(TypedDict):
    """Focus distribution by tag."""

    tagDurations: dict[str, int]


# =============================================================================
# Habits
# =============================================================================


class HabitCheckinQueryV2(TypedDict):
    """Habit check-in query request."""

    habitIds: list[str]
    afterStamp: int


# =============================================================================
# Trash
# =============================================================================


class TrashResponseV2(TypedDict):
    """V2 API trash response."""

    tasks: list[TaskV2]

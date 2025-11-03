"""Task management module for orchestrating subagent execution.

This module provides classes and utilities for creating, managing, and tracking
tasks that are assigned to subagents within the multi-agent system.

Public API:
    - Task: Represents a task to be executed by a subagent
    - TaskStatus: Enum for task lifecycle states
    - ContextBootstrapItem: File/directory to be read into subagent context
    - TaskManager: Manages task lifecycle and orchestrates subagent execution
    - TaskStore: Stores and retrieves tasks
    - create_task_manager: Factory function for creating TaskManager instances
    - task_simbols_map: Mapping of task statuses to symbols for display
"""

from src.core.task.task import (
    Task,
    TaskStatus,
)

from src.core.task.task_manager import (
    TaskManager,
    create_task_manager,
)

from src.core.task.task_store import (
    TaskStore,
)

__all__ = [
    "Task",
    "TaskStatus",
    "TaskManager",
    "create_task_manager",
    "TaskStore",
]


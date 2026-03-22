"""
Task module — manages the lifecycle of tasks delegated to subagents.

Public API:
    Task, TaskStatus    — data models
    TaskManager         — task lifecycle orchestration
    create_task_manager — factory function
    TaskStore           — in-memory task storage
"""
from src.core.task.task import Task, TaskStatus
from src.core.task.task_manager import TaskManager, create_task_manager
from src.core.task.task_store import TaskStore

__all__ = [
    "Task",
    "TaskStatus",
    "TaskManager",
    "create_task_manager",
    "TaskStore",
]

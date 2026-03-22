import logging
from typing import Dict, Any

from src.core.action import TaskCreateAction
from src.core.task.task import Task, TaskStatus
from src.core.task.task_store import TaskStore

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self, task_store: TaskStore):
        self.task_store = task_store
        self.task_trajectories: Dict[str, Dict[str, Any]] = {}

    def create_task(self, action: TaskCreateAction) -> Task:
        logger.info(f"Creating task: {action.title}")
        return self.task_store.create_task(
            agent_name=action.agent_name,
            title=action.title,
            description=action.description,
            context_refs=action.context_refs,
            context_bootstrap=action.context_bootstrap,
        )

    def process_task_result(self, task: Task) -> Dict[str, Any]:
        return {}


    def get_task(self, task_id: str) -> Task | None:
        return self.task_store.get_task(task_id)

    def get_and_clear_task_trajectories(self) -> Dict[str, Dict[str, Any]]:
        trajectories = self.task_trajectories.copy()
        self.task_trajectories.clear()
        return trajectories


def create_task_manager() -> TaskManager:
    return TaskManager(task_store=TaskStore())

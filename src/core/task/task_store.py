import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.core.context import Context
from src.core.task.task import Task, ContextBootstrapItem, TaskStatus

logger = logging.getLogger(__name__)

class TaskStore:

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.context_store: Dict[str, Context] = {}
        self.task_counter = 0


    def create_task(
        self,
        agent_name: str,
        title: str,
        description: str,
        context_refs: List[str],
        context_bootstrap: List[dict]
    ) -> Task:
        self.task_counter += 1
        task_id = f"task_{self.task_counter:03d}"

        # Convert bootstrap dicts to objects
        bootstrap_items = [
            ContextBootstrapItem(path=item['path'], reason=item['reason'])
            for item in context_bootstrap
        ]

        task = Task(
            task_id=task_id,
            agent_name=agent_name,
            title=title,
            description=description,
            context_refs=context_refs,
            context_bootstrap=bootstrap_items
        )

        self.tasks[task_id] = task
        logger.info(f"Created task {task_id}: {title}")

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update the status of a task.

        Returns:
            True if successful, False if task not found
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return False

        task.status = status
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now().isoformat()

        logger.info(f"Updated task {task_id} status to {status.value}")
        return True

    def task_summary(self) -> str:
        """Return formatted view of all tasks with their statuses."""
        if not self.tasks:
            return "No tasks created yet."

        lines = ["Tasks:"]
        for task_id, task in self.tasks.items():
            status_symbol = task_simbols_map.get(task.status, "?")
            lines.append(f"  {status_symbol} [{task_id}] {task.title} ({task.agent_name})")
            lines.append(f"      Status: {task.status.value}")

            if task.context_refs:
                lines.append(f"      Context refs: {', '.join(task.context_refs)}")

            if task.context_bootstrap:
                bootstrap_str = ', '.join([item.path for item in task.context_bootstrap])
                lines.append(f"      Bootstrap: {bootstrap_str}")

            if task.result:
                lines.append(f"      Result: {json.dumps(task.result)}")
            if task.completed_at:
                lines.append(f"      Completed at: {task.completed_at}")

        return "\n".join(lines)


task_simbols_map = {
    TaskStatus.CREATED: "○",
    TaskStatus.COMPLETED: "●",
    TaskStatus.FAILED: "✗"
}

import json
from datetime import datetime
from typing import Dict, List, Optional

from src.core.task.task import Task, ContextBootstrapItem, TaskStatus
from src.misc import pretty_log

task_simbols_map = {
    TaskStatus.CREATED: "○",
    TaskStatus.COMPLETED: "●",
    TaskStatus.FAILED: "✗"
}

class TaskStore:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.task_counter: int = 0

    def create_task(
        self,
        agent_name: str,
        title: str,
        description: str,
        context_refs: List[str],
        context_bootstrap: List[dict],
    ) -> Task:
        self.task_counter += 1
        task_id = f"task_{self.task_counter:03d}"
        bootstrap_items = [
            ContextBootstrapItem(path=item["path"], reason=item["reason"])
            for item in context_bootstrap
        ]
        task = Task(
            task_id=task_id,
            agent_name=agent_name,
            title=title,
            description=description,
            context_refs=context_refs,
            context_bootstrap=bootstrap_items,
        )
        self.tasks[task_id] = task
        pretty_log.info(f"Created task {task_id}: {title}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            pretty_log.warning(f"Task {task_id} not found")
            return False
        task.status = status
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now().isoformat()
        pretty_log.info(f"Updated task {task_id} status to {status.value}")
        return True

    def task_summary(self) -> str:
        if not self.tasks:
            return "No tasks created yet."

        lines = ["Tasks:"]
        for task_id, task in self.tasks.items():
            symbol = task_simbols_map.get(task.status, "?")
            lines.append(f"  {symbol} [{task_id}] {task.title} ({task.agent_name})")
            lines.append(f"      Status: {task.status.value}")
            if task.context_refs:
                lines.append(f"      Context refs: {', '.join(task.context_refs)}")
            if task.context_bootstrap:
                paths = ", ".join(item.path for item in task.context_bootstrap)
                lines.append(f"      Bootstrap: {paths}")
            if task.result is not None:
                lines.append(f"      Result: {json.dumps(task.result)}")
            if task.completed_at is not None:
                lines.append(f"      Completed at: {task.completed_at}")
        return "\n".join(lines)

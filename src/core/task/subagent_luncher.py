import logging
from typing import Dict, List, Tuple


from src.core.common.utils import format_tool_output
from src.core.task import Task, TaskManager
from src.misc import pretty_log

logger = logging.getLogger(__name__)


class AgentLauncher:
    def __init__(
        self,
        task_manager: TaskManager,
    ):
        self.task_manager = task_manager

    def launch(self, task_id: str) -> Tuple[str, bool]:
        task = self.task_manager.get_task(task_id)
        if not task:
            error_msg = f"[ERROR] Task {task_id} not found"
            pretty_log.error(error_msg, "ORCHESTRATOR")
            return format_tool_output("subagent", error_msg), True

        # Lunch the subagent here (this is a placeholder, actual implementation would depend on how subagents are defined and executed)

        result = self.task_manager.process_task_result(task)
        response_lines = [
            f"Subagent completed task {task_id}",
            f"Contexts stored: {', '.join(result['context_ids_stored'])}",
        ]
        if result["comments"]:
            response_lines.append(f"Comments: {result['comments']}")
        return format_tool_output("subagent", "\n".join(response_lines)), False



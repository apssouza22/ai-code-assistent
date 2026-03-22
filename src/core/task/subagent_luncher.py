from typing import Dict, List, Tuple


from src.core.common.utils import format_tool_output
from src.core.context import ContextStore
from src.core.task import Task, TaskManager
from src.core.task.subagent_report import SubagentReport
from src.misc import pretty_log


class AgentLauncher:
    def __init__(
        self,
        task_manager: TaskManager,
        context_store: ContextStore,
    ):
        self.context_store = context_store
        self.task_manager = task_manager

    def launch(self, task_id: str) -> Tuple[str, bool]:
        task = self.task_manager.get_task(task_id)
        if not task:
            error_msg = f"[ERROR] Task {task_id} not found"
            pretty_log.error(error_msg, "ORCHESTRATOR")
            return format_tool_output("subagent", error_msg), True

        bootstrap_ctx, task_context = self._build_context(task)
        # Lunch the subagent here (this is a placeholder, actual implementation would depend on how subagents are defined and executed)
        subagent_result = SubagentReport(
            contexts=[],
            comments="Subagent executed successfully",
        )
        result = self.task_manager.process_task_result(task, subagent_result)
        response_lines = [
            f"Subagent completed task {task_id}",
            f"Contexts stored: {', '.join(result['context_ids_stored'])}",
        ]
        if result["comments"]:
            response_lines.append(f"Comments: {result['comments']}")
        return format_tool_output("subagent", "\n".join(response_lines)), False


    def _build_context(self, task: Task) -> Tuple[list, dict]:
        task_context = self._get_context_by_ids(task.context_refs)
        file_context = []
        if not task.context_bootstrap:
            return file_context, task_context

        # TODO: implement the file search and retrieval logic here, for now we just log the intention
        pretty_log.debug(f"Task {task.task_id} requested bootstrap context: {task.context_bootstrap}", "ORCHESTRATOR")


        return file_context, task_context

    def _get_context_by_ids(self, ids: List[str]) -> Dict[str, str]:
        """Get contexts by their IDs."""
        contexts = {}
        for context_id in ids:
            context = self.context_store.get_context(context_id)
            if context:
                contexts[context_id] = context.content
                pretty_log.debug(f"Included context {context_id} in subagent task", "ORCHESTRATOR")
            else:
                pretty_log.warning(f"Context {context_id} not found")
        return contexts

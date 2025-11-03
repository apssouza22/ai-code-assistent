import logging
from typing import Dict, List, Tuple

from src.core.agent import AgentManager, SubagentTask
from src.core.common.utils import format_tool_output
from src.core.context import ContextStore
from src.core.task import Task, TaskManager
from src.core.bash import FileManager, SearchManager
from src.misc import pretty_log

logger = logging.getLogger(__name__)


class AgentLauncher:

    def __init__(self,
        agent_manager: AgentManager,
        task_manager:TaskManager,
        context_store: ContextStore,
        file_manager: FileManager,
        search_manager: SearchManager
    ):
        self.search_manager = search_manager
        self.file_manager = file_manager
        self.task_manager = task_manager
        self.context_store = context_store
        self.agent_manager = agent_manager


    def launch(self, task_id) -> Tuple[str, bool]:
        """Launch the appropriate subagent for the specified task."""

        task = self.task_manager.get_task(task_id)
        if not task:
            error_msg = f"[ERROR] Task {task_id} not found"
            pretty_log.error(error_msg, "ORCHESTRATOR")
            return format_tool_output("subagent", error_msg), True

        bootstrap_ctx, task_context = self._build_context(task)
        agent_task = SubagentTask(
            agent_name=task.agent_name,
            instruction=task.title,
            title=task.title,
            description=task.description,
            task_id=task_id,
            task_context=task_context,
            bootstrap_ctx=bootstrap_ctx,
        )
        agent_report, error = self.agent_manager.launch_subagent(agent_task)
        if not agent_report:
            return error, True

        result = self.task_manager.process_task_result(task, agent_report)

        response_lines = [
            f"Subagent completed task {task_id}",
            f"Contexts stored: {', '.join(result['context_ids_stored'])}",
        ]
        if result["comments"]:
            response_lines.append(f"Comments: {result['comments']}")
        response = "\n".join(response_lines)

        return format_tool_output("subagent", response), False

    def _build_context(self, task: Task) -> Tuple[list, dict]:
        task_context = self._get_context_by_ids(task.context_refs)
        bootstrap_ctxts = []
        if not task.context_bootstrap:
            return bootstrap_ctxts, task_context

        for item in task.context_bootstrap:
            path = item.path
            reason = item.reason
            is_dir = path.endswith("/")
            if is_dir:
                ls_result, _ = self.search_manager.ls(path, ignore=[])
                bootstrap_ctxts.append({"path": path, "content": ls_result, "reason": reason})
            else:
                file_result, _ = self.file_manager.read_file(path, offset=0, limit=1000)
                bootstrap_ctxts.append({"path": path, "content": file_result, "reason": reason})

        return bootstrap_ctxts, task_context

    def _get_context_by_ids(self, ids: List[str]) -> Dict[str, str]:
        """Get contexts by their IDs."""
        contexts = {}
        for ref in ids:
            context = self.context_store.get_context(ref)
            if context:
                contexts[ref] = context.content
            else:
                logger.warning(f"Context {ref} not found")
        return contexts


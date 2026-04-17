from typing import Dict, List, Tuple

from src.core.agent import SubagentTask, Agent
from src.core.common.utils import format_tool_output
from src.core.context import ContextStore
from src.core.task import Task, TaskManager
from src.misc import pretty_log


class AgentLauncher:
    def __init__(
        self,
        task_manager: TaskManager,
        context_store: ContextStore,
        agents: dict[str, Agent]
    ):
        self.agents = agents
        self.context_store = context_store
        self.task_manager = task_manager

    def launch(self, task_id: str) -> Tuple[str, bool]:
        task = self.task_manager.get_task(task_id)
        if not task:
            error_msg = f"[ERROR] Task {task_id} not found"
            pretty_log.error(error_msg, "ORCHESTRATOR")
            return format_tool_output("subagent", error_msg), True

        agent: Agent | None = self.agents.get(task.agent_name)
        if not agent:
            error_msg = f"[ERROR] Agent {task.agent_name} not found"
            pretty_log.error(error_msg, "ORCHESTRATOR")
            return format_tool_output("subagent", error_msg), True

        agent_task = self._get_agent_task(task)
        subagent_result = agent.run_task(agent_task)

        result = self.task_manager.process_task_result(task, subagent_result)
        response_lines = [
            f"Subagent completed task {task_id}",
            f"Contexts stored: {', '.join(result['context_ids_stored'])}",
        ]

        if result["comments"]:
            response_lines.append(f"Comments: {result['comments']}")

        return format_tool_output("subagent", "\n".join(response_lines)), False

    def _get_agent_task(self, task: Task) -> SubagentTask:
        bootstrap_ctx, task_context = self._build_context(task)
        return SubagentTask(
            agent_name=task.agent_name,
            instruction=task.description,
            title=task.title,
            task_id=task.task_id,
            task_context=task_context,
            relevant_files=bootstrap_ctx,
            description=None
        )

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

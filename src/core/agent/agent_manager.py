import logging
from typing import Tuple, Optional, Dict

from src.core.agent.subagent import SubagentTask, Subagent
from src.core.agent.subagent_report import SubagentReport
from src.core.common.utils import format_tool_output
from src.misc import pretty_log

logger = logging.getLogger(__name__)
class AgentManager:

    def __init__(self,agents: list[Subagent]):
        self.agents: Dict[str, Subagent] = {agent.agent_name: agent for agent in agents}

    def launch_subagent(self, task: SubagentTask) -> Tuple[Optional[SubagentReport],  str]:
        """Launch the appropriate subagent for the specified task."""
        agent = self.agents.get(task.agent_name)
        if not agent:
            error_msg = f"[ERROR] No agent configured for type '{task.agent_name}'"
            return None, format_tool_output("subagent", error_msg)

        pretty_log.info(f"Launching {task.agent_name} agent for task: {task.title}", "ORCHESTRATOR")
        report = agent.run_task(task)

        pretty_log.success(f"Agent {task.agent_name} completed task {task.title}({task.task_id})", "ORCHESTRATOR")
        pretty_log.success(f"Agent report: {report.comments}", "ORCHESTRATOR")
        return report, ""




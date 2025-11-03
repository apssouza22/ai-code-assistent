"""Subagent action handler."""

from typing import Tuple, Optional

from src.core.action.actions import LaunchSubagentAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.common.utils import format_tool_output
from src.core.task.subagent_luncher import AgentLauncher


class LaunchSubagentActionHandler(ActionHandlerInterface):
    """Handler for launching subagents."""

    def __init__(self, subagent_launcher: Optional[AgentLauncher] = None):
        self.subagent_launcher = subagent_launcher

    def handle(self, action: LaunchSubagentAction) -> Tuple[str, bool]:
        """Handle launching a subagent for a task."""
        if not self.subagent_launcher:
            error_msg = "[ERROR] Launching subagents is not available in this context"
            return format_tool_output("subagent", error_msg), True

        return self.subagent_launcher.launch(action.task_id)


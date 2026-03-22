from typing import Tuple, Optional

from src.core.action.actions import LaunchSubagentAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.task.subagent_luncher import AgentLauncher


class LaunchSubagentActionHandler(ActionHandlerInterface):
    def __init__(self, subagent_launcher: Optional[AgentLauncher] = None):
        self.subagent_launcher = subagent_launcher

    def handle(self, action: LaunchSubagentAction) -> Tuple[str, bool]:
        return self.subagent_launcher.launch(action.task_id)

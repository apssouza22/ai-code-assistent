from src.core.action import TaskCreateAction, ActionHandlerInterface
from src.core.common.utils import format_tool_output
from src.core.task.subagent_luncher import AgentLauncher
from src.core.task import TaskManager
from src.misc import pretty_log


class CreateTaskActionHandler(ActionHandlerInterface):
    def __init__(self, task_manager: TaskManager, agent_launcher: AgentLauncher):
        self.task_manager = task_manager
        self.agent_launcher = agent_launcher

    def handle(self, action: TaskCreateAction) -> tuple[str, bool]:
        try:
            task = self.task_manager.create_task(action)
            response = f"Created task {task.task_id}: {action.title}"
            if action.auto_launch:
                launch_response, launch_error = self.agent_launcher.launch(task.task_id)
                response += f"\n{launch_response}"
                return format_tool_output("task", response), launch_error

            return format_tool_output("task", response), False
        except Exception as exc:
            error_msg = f"[ERROR] Failed to create task: {str(exc)}"
            pretty_log.error(error_msg, "ORCHESTRATOR")
            return format_tool_output("task", error_msg), True

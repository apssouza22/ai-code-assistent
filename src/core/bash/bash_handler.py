"""Bash action handler."""

from typing import Tuple

from src.core.action.actions import BashAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.common.utils import format_tool_output
from src.core.bash import CommandExecutor


class BashActionHandler(ActionHandlerInterface):
    """Handler for bash command execution."""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor

    def handle(self, action: BashAction) -> Tuple[str, bool]:
        """Handle bash command execution."""
        try:
            if action.block:
                output, exit_code = self.executor.execute(
                    action.cmd,
                    timeout=action.timeout_secs
                )
            else:
                # Non-blocking execution
                self.executor.execute_background(action.cmd)
                output = "Command started in background"
                exit_code = 0

            is_error = exit_code != 0
            return format_tool_output("bash", output), is_error

        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            return format_tool_output("bash", error_msg), True


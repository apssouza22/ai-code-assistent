from typing import Tuple

from src.core.action.actions import FinishAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.common.utils import format_tool_output


class FinishActionHandler(ActionHandlerInterface):
    def handle(self, action: FinishAction) -> Tuple[str, bool]:
        response = f"Task marked as complete: {action.message}"
        return format_tool_output("finish", response), False

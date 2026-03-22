from typing import Tuple

from src.core.action.actions import ReportAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.common.utils import format_tool_output


class ReportActionHandler(ActionHandlerInterface):
    def handle(self, action: ReportAction) -> Tuple[str, bool]:
        return format_tool_output("report", "Report submission successful"), False

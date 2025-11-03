"""Report action handler."""

from typing import Tuple

from src.core.action.actions import ReportAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.common.utils import format_tool_output


class ReportActionHandler(ActionHandlerInterface):
    """Handler for report action."""

    def handle(self, action: ReportAction) -> Tuple[str, bool]:
        """Handle report action."""
        return format_tool_output("report", "Report submission successful"), False


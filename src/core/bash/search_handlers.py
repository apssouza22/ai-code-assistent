"""Search action handlers."""

from typing import Tuple

from src.core.action.actions import GrepAction, GlobAction, LSAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.common.utils import format_tool_output
from src.core.bash import SearchManager


class GrepActionHandler(ActionHandlerInterface):
    """Handler for grep search."""

    def __init__(self, search_manager: SearchManager):
        self.search_manager = search_manager

    def handle(self, action: GrepAction) -> Tuple[str, bool]:
        """Handle grep search."""
        content, is_error = self.search_manager.grep(
            action.pattern, action.path, action.include
        )
        return format_tool_output("search", content), is_error


class GlobActionHandler(ActionHandlerInterface):
    """Handler for glob search."""

    def __init__(self, search_manager: SearchManager):
        self.search_manager = search_manager

    def handle(self, action: GlobAction) -> Tuple[str, bool]:
        """Handle glob search."""
        content, is_error = self.search_manager.glob(
            action.pattern, action.path
        )
        return format_tool_output("search", content), is_error


class LSActionHandler(ActionHandlerInterface):
    """Handler for ls command."""

    def __init__(self, search_manager: SearchManager):
        self.search_manager = search_manager

    def handle(self, action: LSAction) -> Tuple[str, bool]:
        """Handle ls command."""
        content, is_error = self.search_manager.ls(
            action.path, action.ignore
        )
        return format_tool_output("search", content), is_error


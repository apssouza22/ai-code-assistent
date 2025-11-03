"""Scratchpad/note action handlers."""

from typing import Tuple

from src.core.action.actions import AddNoteAction, ViewAllNotesAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.common.utils import format_tool_output
from src.core.notepad.notepad_manager import ScratchpadManager


class AddNoteActionHandler(ActionHandlerInterface):
    """Handler for adding notes to scratchpad."""

    def __init__(self, scratchpad_manager: ScratchpadManager):
        self.scratchpad_manager = scratchpad_manager

    def handle(self, action: AddNoteAction) -> Tuple[str, bool]:
        """Handle adding a note to scratchpad."""
        if not action.content:
            return format_tool_output("scratchpad", "[ERROR] Cannot add empty note"), True

        note_idx = self.scratchpad_manager.add_note(action.content)
        response = f"Added note {note_idx + 1} to scratchpad"
        return format_tool_output("scratchpad", response), False


class ViewAllNotesActionHandler(ActionHandlerInterface):
    """Handler for viewing all notes."""

    def __init__(self, scratchpad_manager: ScratchpadManager):
        self.scratchpad_manager = scratchpad_manager

    def handle(self, action: ViewAllNotesAction) -> Tuple[str, bool]:
        """Handle viewing all notes."""
        return format_tool_output("scratchpad", self.scratchpad_manager.view_all()), False


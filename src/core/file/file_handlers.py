"""File action handlers."""

from typing import Tuple

from src.core.action.actions import (
    ReadAction,
    WriteAction,
    EditAction,
    MultiEditAction,
    FileMetadataAction,
    WriteTempScriptAction,
)
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.bash import FileManager
from src.core.common.utils import format_tool_output


class ReadActionHandler(ActionHandlerInterface):
    """Handler for reading files."""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    def handle(self, action: ReadAction) -> Tuple[str, bool]:
        """Handle reading a file."""
        content, is_error = self.file_manager.read_file(
            action.file_path, action.offset, action.limit
        )
        return format_tool_output("file", content), is_error


class WriteActionHandler(ActionHandlerInterface):
    """Handler for writing files."""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    def handle(self, action: WriteAction) -> Tuple[str, bool]:
        """Handle writing a file."""
        content, is_error = self.file_manager.write_file(
            action.file_path, action.content
        )
        return format_tool_output("file", content), is_error


class EditActionHandler(ActionHandlerInterface):
    """Handler for editing files."""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    def handle(self, action: EditAction) -> Tuple[str, bool]:
        """Handle editing a file."""
        content, is_error = self.file_manager.edit_file(
            action.file_path, action.old_string, action.new_string, action.replace_all
        )
        return format_tool_output("file", content), is_error


class MultiEditActionHandler(ActionHandlerInterface):
    """Handler for multiple edits to a file."""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    def handle(self, action: MultiEditAction) -> Tuple[str, bool]:
        """Handle multiple edits to a file."""
        edits = [(e.old_string, e.new_string, e.replace_all) for e in action.edits]
        content, is_error = self.file_manager.multi_edit_file(
            action.file_path, edits
        )
        return format_tool_output("file", content), is_error


class FileMetadataActionHandler(ActionHandlerInterface):
    """Handler for file metadata requests."""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    def handle(self, action: FileMetadataAction) -> Tuple[str, bool]:
        """Handle file metadata request."""
        content, is_error = self.file_manager.get_metadata(action.file_paths)
        return format_tool_output("file", content), is_error


class WriteTempScriptActionHandler(ActionHandlerInterface):
    """Handler for writing temporary script files."""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    def handle(self, action: WriteTempScriptAction) -> Tuple[str, bool]:
        """Handle writing a temporary script file.

        This uses the same underlying file write functionality but is specifically
        intended for temporary scripts used during exploration/testing.
        """
        content, is_error = self.file_manager.write_file(
            action.file_path, action.content
        )
        return format_tool_output("file", content), is_error

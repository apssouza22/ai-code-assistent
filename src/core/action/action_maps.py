from typing import Dict, Type

from src.core.action.actions import (
    Action,
    BashAction, FinishAction, BatchTodoAction,
    ReadAction, WriteAction, EditAction, MultiEditAction, FileMetadataAction,
    GrepAction, GlobAction, LSAction,
    AddNoteAction, ViewAllNotesAction,
    TaskCreateAction, AddContextAction, LaunchSubagentAction, ReportAction,
    WriteTempScriptAction, UserInputAction
)

# Map XML tags to Action classes
ACTION_MAP: Dict[str, Type[Action]] = {
    # Core actions
    'bash': BashAction,
    'finish': FinishAction,
    'user_input': UserInputAction,

    # Todo actions
    'todo': BatchTodoAction,

    # File actions
    'read_file': ReadAction,
    'write_file': WriteAction,
    'edit_file': EditAction,
    'multi_edit_file': MultiEditAction,
    'file_metadata': FileMetadataAction,

    # Search actions
    'grep': GrepAction,
    'glob': GlobAction,
    'ls': LSAction,

    # Scratchpad actions
    'add_note': AddNoteAction,
    'view_all_notes': ViewAllNotesAction,

    # Task management
    'task_create': TaskCreateAction,
    'add_context': AddContextAction,
    'launch_subagent': LaunchSubagentAction,
    'report': ReportAction,
    'write_temp_script': WriteTempScriptAction,
}

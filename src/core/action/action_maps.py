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

    # Todo actions (unified under one tag)
    'todo': BatchTodoAction,

    # Task management
    'task_create': TaskCreateAction,
    'add_context': AddContextAction,
    'launch_subagent': LaunchSubagentAction,
    'report': ReportAction,
    'write_temp_script': WriteTempScriptAction,
}

# Sub-action mappings for tags that have multiple action types
FILE_ACTIONS: Dict[str, Type[Action]] = {
    'read': ReadAction,
    'write': WriteAction,
    'edit': EditAction,
    'multi_edit': MultiEditAction,
    'metadata': FileMetadataAction,
}

SEARCH_ACTIONS: Dict[str, Type[Action]] = {
    'grep': GrepAction,
    'glob': GlobAction,
    'ls': LSAction,
}

SCRATCHPAD_ACTIONS: Dict[str, Type[Action]] = {
    'add_note': AddNoteAction,
    'view_all_notes': ViewAllNotesAction,
}

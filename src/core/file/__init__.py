from typing import Dict, Callable

from src.core.action.actions import ReadAction, MultiEditAction, FileMetadataAction, WriteTempScriptAction, WriteAction, EditAction
from src.core.backend import CommandExecutor
from src.core.file.file_handlers import ReadActionHandler, WriteActionHandler, EditActionHandler, MultiEditActionHandler, FileMetadataActionHandler, WriteTempScriptActionHandler


def get_file_handlers(executor: CommandExecutor) -> Dict[type, Callable]:
    return {
        ReadAction: ReadActionHandler(executor).handle,
        WriteAction: WriteActionHandler(executor).handle,
        EditAction: EditActionHandler(executor).handle,
        MultiEditAction: MultiEditActionHandler(executor).handle,
        FileMetadataAction: FileMetadataActionHandler(executor).handle,
        WriteTempScriptAction: WriteTempScriptActionHandler(executor).handle,
    }

"""File action handlers."""

import base64
import os
from typing import List, Optional, Tuple

from src.core.action.actions import (
    ReadAction,
    WriteAction,
    EditAction,
    MultiEditAction,
    FileMetadataAction,
    WriteTempScriptAction,
)
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.backend import CommandExecutor
from src.core.common.utils import format_tool_output
from src.misc import pretty_log


class ReadActionHandler(ActionHandlerInterface):
    def __init__(self, executor: CommandExecutor):
        self._executor = executor

    def handle(self, action: ReadAction) -> Tuple[str, bool]:
        content, is_error = read_file(self._executor, action.file_path, action.offset, action.limit)
        return format_tool_output("file", content), is_error


class WriteActionHandler(ActionHandlerInterface):
    def __init__(self, executor: CommandExecutor):
        self._executor = executor

    def handle(self, action: WriteAction) -> Tuple[str, bool]:
        content, is_error = _write_file(self._executor, action.file_path, action.content)
        return format_tool_output("file", content), is_error


class EditActionHandler(ActionHandlerInterface):
    def __init__(self, executor: CommandExecutor):
        self._executor = executor

    def handle(self, action: EditAction) -> Tuple[str, bool]:
        content, is_error = _edit_file(
            self._executor,
            action.file_path,
            action.old_string,
            action.new_string,
            action.replace_all,
        )
        return format_tool_output("file", content), is_error


class MultiEditActionHandler(ActionHandlerInterface):
    def __init__(self, executor: CommandExecutor):
        self._executor = executor

    def handle(self, action: MultiEditAction) -> Tuple[str, bool]:
        edits = [(e.old_string, e.new_string, e.replace_all) for e in action.edits]
        content, is_error = _multi_edit_file(self._executor, action.file_path, edits)
        return format_tool_output("file", content), is_error


class FileMetadataActionHandler(ActionHandlerInterface):
    def __init__(self, executor: CommandExecutor):
        self._executor = executor

    def handle(self, action: FileMetadataAction) -> Tuple[str, bool]:
        content, is_error = _get_metadata(self._executor, action.file_paths)
        return format_tool_output("file", content), is_error


class WriteTempScriptActionHandler(ActionHandlerInterface):
    def __init__(self, executor: CommandExecutor):
        self._executor = executor

    def handle(self, action: WriteTempScriptAction) -> Tuple[str, bool]:
        content, is_error = _write_file(self._executor, action.file_path, action.content)
        return format_tool_output("file", content), is_error

def _run_command(executor: CommandExecutor, cmd: str, timeout: int = 30) -> Tuple[str, int]:
    return executor.execute(cmd, timeout=timeout)


def read_file(
    executor: CommandExecutor,
    file_path: str,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> Tuple[str, bool]:
    if offset is not None and limit is not None:
        cmd = f"tail -n +{offset} '{file_path}' 2>&1 | head -n {limit} | nl -ba -v {offset}"
    elif limit is not None:
        cmd = f"head -n {limit} '{file_path}' 2>&1 | nl -ba"
    else:
        cmd = f"nl -ba '{file_path}' 2>&1"

    pretty_log.debug(f"[read_file] Reading file with command: {cmd}")
    output, code = _run_command(executor, cmd)

    if "No such file or directory" in output or "cannot open" in output:
        return f"File not found: {file_path}", True

    if code != 0 and output:
        return f"Error reading file: {output}", True

    return output, False


def _write_file(executor: CommandExecutor, file_path: str, content: str) -> Tuple[str, bool]:
    dir_path = os.path.dirname(file_path)
    if dir_path:
        mkdir_cmd = f"mkdir -p '{dir_path}'"
        _run_command(executor, mkdir_cmd)

    encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
    write_cmd = f"echo '{encoded_content}' | base64 -d > '{file_path}'"

    output, code = _run_command(executor, write_cmd)

    if code != 0:
        return f"Error writing file: {output}", True

    return f"Successfully wrote to {file_path}", False


def _edit_file(
    executor: CommandExecutor,
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> Tuple[str, bool]:
    backup_cmd = f"cp '{file_path}' '{file_path}.bak' 2>&1"
    output, code = _run_command(executor, backup_cmd)

    if "No such file or directory" in output or code != 0:
        return f"File not found: {file_path}", True

    backup_cmd = f"cp '{file_path}' '{file_path}.bak'"
    _run_command(executor, backup_cmd)

    old_encoded = base64.b64encode(old_string.encode("utf-8")).decode("ascii")
    new_encoded = base64.b64encode(new_string.encode("utf-8")).decode("ascii")

    replace_count = -1 if replace_all else 1
    python_cmd = f"""python -c "
import base64
with open('{file_path}', 'r') as f:
    content = f.read()
old_str = base64.b64decode('{old_encoded}').decode('utf-8')
new_str = base64.b64decode('{new_encoded}').decode('utf-8')
content = content.replace(old_str, new_str, {replace_count})
with open('{file_path}', 'w') as f:
    f.write(content)
" """

    output, code = _run_command(executor, python_cmd)

    cleanup_cmd = f"rm -f '{file_path}.bak'"
    _run_command(executor, cleanup_cmd)

    if code != 0:
        return f"Error editing file: {output}", True

    msg = "all occurrences" if replace_all else "first occurrence"
    return f"Successfully replaced {msg} in {file_path}", False


def _multi_edit_file(
    executor: CommandExecutor, file_path: str, edits: List[Tuple[str, str, bool]]
) -> Tuple[str, bool]:
    results = []

    for i, (old_string, new_string, replace_all) in enumerate(edits):
        result, is_error = _edit_file(executor, file_path, old_string, new_string, replace_all)

        if is_error and "No matches found" not in result:
            return f"Error on edit {i + 1}: {result}", True

        results.append(f"Edit {i + 1}: {result}")

    return "\n".join(results), False


def _get_metadata(executor: CommandExecutor, file_paths: List[str]) -> Tuple[str, bool]:
    results = []

    for file_path in file_paths[:10]:
        stat_cmd = f"""
            if [ -e '{file_path}' ]; then
                stat -c '%s %Y %U:%G %a' '{file_path}' 2>/dev/null || stat -f '%z %m %Su:%Sg %Lp' '{file_path}'
                echo -n ' '
                file -b '{file_path}' 2>/dev/null || echo 'unknown'
            else
                echo 'not_found'
            fi
            """

        output, _ = _run_command(executor, stat_cmd)

        if "not_found" in output:
            results.append(f"{file_path}: Not found")
        else:
            parts = output.strip().split(maxsplit=4)
            if len(parts) >= 5:
                size, mtime, owner, perms = parts[0], parts[1], parts[2], parts[3]
                filetype = " ".join(parts[4:])
                results.append(
                    f"{file_path}:\n  Size: {size} bytes\n  Type: {filetype}\n"
                    f"  Owner: {owner}\n  Permissions: {perms}"
                )
            else:
                results.append(f"{file_path}: Unable to get metadata")

    return "\n\n".join(results), False


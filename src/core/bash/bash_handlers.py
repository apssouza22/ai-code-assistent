"""Search action handlers."""

from typing import List, Optional, Tuple

from src.core.action.actions import BashAction
from src.core.action.actions import GrepAction, GlobAction, LSAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.backend import CommandExecutor
from src.core.common.utils import format_tool_output


class BashActionHandler(ActionHandlerInterface):
    """Handler for bash command execution."""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor

    def handle(self, action: BashAction) -> Tuple[str, bool]:
        """Handle bash command execution."""
        try:
            if action.block:
                output, exit_code = self.executor.execute(
                    action.cmd,
                    timeout=action.timeout_secs
                )
            else:
                # Non-blocking execution
                self.executor.execute_background(action.cmd)
                output = "Command started in background"
                exit_code = 0

            is_error = exit_code != 0
            return format_tool_output("bash", output), is_error

        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            return format_tool_output("bash", error_msg), True

class GrepActionHandler(ActionHandlerInterface):
    """Handler for grep search."""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor

    def handle(self, action: GrepAction) -> Tuple[str, bool]:
        content, is_error = run_grep(self.executor, action.pattern, action.path, action.include)
        return format_tool_output("grep", content), is_error


class GlobActionHandler(ActionHandlerInterface):
    """Handler for glob search."""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor

    def handle(self, action: GlobAction) -> Tuple[str, bool]:
        content, is_error = run_glob(self.executor, action.pattern, action.path)
        return format_tool_output("glob", content), is_error


class LSActionHandler(ActionHandlerInterface):
    """Handler for ls command."""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor

    def handle(self, action: LSAction) -> Tuple[str, bool]:
        content, is_error = run_ls(self.executor, action.path, action.ignore)
        return format_tool_output("ls", content), is_error


def _run_command(executor: CommandExecutor, cmd: str, timeout: int = 30) -> Tuple[str, int]:
    return executor.execute(cmd, timeout=timeout)


def run_grep(
    executor: CommandExecutor,
    pattern: str,
    path: Optional[str] = None,
    include: Optional[str] = None,
) -> Tuple[str, bool]:
    grep_flags = [
        "-r",
        "-n",
        "-H",
        "--color=never",
    ]

    if include:
        grep_flags.append(f"--include='{include}'")

    search_path = path or "."
    escaped_pattern = pattern.replace("'", "'\"'\"'")
    cmd = f"grep {' '.join(grep_flags)} '{escaped_pattern}' '{search_path}' 2>/dev/null | head -n 100"

    output, code = _run_command(executor, cmd)

    if code == 1 and not output:
        return "No matches found", False
    elif code > 1:
        return f"Error during search: {output}", True

    lines = output.strip().split("\n") if output.strip() else []
    if len(lines) == 100:
        result = "\n".join(lines) + "\n\n[Output truncated to 100 matches]"
    else:
        result = output if output else "No matches found"

    return result, False


def run_glob(executor: CommandExecutor, pattern: str, path: Optional[str] = None) -> Tuple[str, bool]:
    search_path = path or "."
    find_pattern = pattern.replace("**/", "*/").replace("*", "*")
    cmd = f"find '{search_path}' -name '{find_pattern}' -type f 2>/dev/null | head -n 100 | sort"

    output, code = _run_command(executor, cmd)

    if code != 0:
        return f"Error during file search: {output}", True

    lines = output.strip().split("\n") if output.strip() else []
    if not lines or (len(lines) == 1 and not lines[0]):
        return "No files found matching pattern", False

    if len(lines) == 100:
        result = "\n".join(lines) + "\n\n[Output truncated to 100 files]"
    else:
        result = "\n".join(lines)

    return result, False


def run_ls(
    executor: CommandExecutor, path: str, ignore: Optional[List[str]] = None
) -> Tuple[str, bool]:
    check_cmd = (
        f"test -d '{path}' && echo 'dir' || (test -e '{path}' && echo 'not_dir' || echo 'not_found')"
    )
    output, _ = _run_command(executor, check_cmd)

    if "not_found" in output:
        return f"Path not found: {path}", True
    elif "not_dir" in output:
        return f"Path is not a directory: {path}", True

    ls_cmd = f"ls -la '{path}' 2>/dev/null"
    output, code = _run_command(executor, ls_cmd)

    if code != 0:
        return f"Error listing directory: {output}", True

    if ignore and output:
        lines = output.strip().split("\n")
        filtered_lines = []

        for line in lines:
            if line.startswith("total") or not line.strip():
                filtered_lines.append(line)
                continue

            parts = line.split()
            if len(parts) >= 9:
                filename = " ".join(parts[8:])
                should_ignore = False
                for pattern in ignore:
                    if pattern.startswith("*") and filename.endswith(pattern[1:]):
                        should_ignore = True
                        break
                    elif pattern.endswith("*") and filename.startswith(pattern[:-1]):
                        should_ignore = True
                        break
                    elif pattern in filename:
                        should_ignore = True
                        break

                if not should_ignore:
                    filtered_lines.append(line)
            else:
                filtered_lines.append(line)

        output = "\n".join(filtered_lines)

    return output, False


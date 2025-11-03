#!/usr/bin/env python3
"""Unit tests for individual action handlers."""

import pytest
from unittest.mock import Mock

from src.core.action.actions import (
    BashAction,
    FinishAction,
    BatchTodoAction,
    TodoOperation,
    AddNoteAction,
    ViewAllNotesAction,
    ReadAction,
    WriteAction,
    EditAction,
    GrepAction,
    AddContextAction,
    ReportAction,
)
from src.core.bash.bash_handler import BashActionHandler
from src.core.action.handlers.finish_handler import FinishActionHandler
from src.core.todo.todo_handler import BatchTodoActionHandler
from src.core.notepad.note_handlers import AddNoteActionHandler, ViewAllNotesActionHandler
from src.core.file.file_handlers import ReadActionHandler, WriteActionHandler, EditActionHandler
from src.core.bash.search_handlers import GrepActionHandler
from src.core.context.context_handler import AddContextActionHandler
from src.core.action.handlers.report_handler import ReportActionHandler
from src.core.context import Context


class TestBashActionHandler:
    """Test BashActionHandler."""

    def test_blocking_command_success(self):
        """Test successful blocking command execution."""
        executor = Mock()
        executor.execute.return_value = ("output", 0)

        handler = BashActionHandler(executor)
        action = BashAction(cmd="ls -la", block=True, timeout_secs=30)

        result, is_error = handler.handle(action)

        assert not is_error
        assert "output" in result
        executor.execute.assert_called_once_with("ls -la", timeout=30)

    def test_blocking_command_error(self):
        """Test blocking command with error."""
        executor = Mock()
        executor.execute.return_value = ("error output", 1)

        handler = BashActionHandler(executor)
        action = BashAction(cmd="invalid_cmd", block=True)

        result, is_error = handler.handle(action)

        assert is_error
        assert "error output" in result

    def test_non_blocking_command(self):
        """Test non-blocking command execution."""
        executor = Mock()

        handler = BashActionHandler(executor)
        action = BashAction(cmd="long_running_cmd", block=False)

        result, is_error = handler.handle(action)

        assert not is_error
        assert "background" in result.lower()
        executor.execute_background.assert_called_once_with("long_running_cmd")

    def test_command_exception(self):
        """Test command execution with exception."""
        executor = Mock()
        executor.execute.side_effect = Exception("Command failed")

        handler = BashActionHandler(executor)
        action = BashAction(cmd="failing_cmd", block=True)

        result, is_error = handler.handle(action)

        assert is_error
        assert "Error executing command" in result


class TestFinishActionHandler:
    """Test FinishActionHandler."""

    def test_finish_action(self):
        """Test finish action handling."""
        handler = FinishActionHandler()
        action = FinishAction(message="Task completed successfully")

        result, is_error = handler.handle(action)

        assert not is_error
        assert "Task completed successfully" in result


class TestBatchTodoActionHandler:
    """Test BatchTodoActionHandler."""

    def test_add_todo(self):
        """Test adding a todo."""
        todo_manager = Mock()
        todo_manager.add_task.return_value = 1

        handler = BatchTodoActionHandler(todo_manager)
        action = BatchTodoAction(
            operations=[TodoOperation(action="add", content="Test task")],
            view_all=False
        )

        result, is_error = handler.handle(action)

        assert not is_error
        assert "Added todo [1]" in result
        todo_manager.add_task.assert_called_once_with("Test task")

    def test_complete_todo(self):
        """Test completing a todo."""
        todo_manager = Mock()
        todo_manager.get_task.return_value = {"status": "pending", "content": "Test task"}

        handler = BatchTodoActionHandler(todo_manager)
        action = BatchTodoAction(
            operations=[TodoOperation(action="complete", task_id=1)],
            view_all=False
        )

        result, is_error = handler.handle(action)

        assert not is_error
        assert "Completed task [1]" in result
        todo_manager.complete_task.assert_called_once_with(1)

    def test_complete_nonexistent_todo(self):
        """Test completing a non-existent todo."""
        todo_manager = Mock()
        todo_manager.get_task.return_value = None

        handler = BatchTodoActionHandler(todo_manager)
        action = BatchTodoAction(
            operations=[TodoOperation(action="complete", task_id=999)],
            view_all=False
        )

        result, is_error = handler.handle(action)

        assert is_error
        assert "Task 999 not found" in result


class TestNoteHandlers:
    """Test note/scratchpad handlers."""

    def test_add_note(self):
        """Test adding a note."""
        scratchpad_manager = Mock()
        scratchpad_manager.add_note.return_value = 0

        handler = AddNoteActionHandler(scratchpad_manager)
        action = AddNoteAction(content="Test note")

        result, is_error = handler.handle(action)

        assert not is_error
        assert "Added note 1" in result
        scratchpad_manager.add_note.assert_called_once_with("Test note")


    def test_view_all_notes(self):
        """Test viewing all notes."""
        scratchpad_manager = Mock()
        scratchpad_manager.view_all.return_value = "Note 1\nNote 2"

        handler = ViewAllNotesActionHandler(scratchpad_manager)
        action = ViewAllNotesAction()

        result, is_error = handler.handle(action)

        assert not is_error
        assert "Note 1" in result


class TestFileHandlers:
    """Test file operation handlers."""

    def test_read_file(self):
        """Test reading a file."""
        file_manager = Mock()
        file_manager.read_file.return_value = ("file content", False)

        handler = ReadActionHandler(file_manager)
        action = ReadAction(file_path="/test/file.txt")

        result, is_error = handler.handle(action)

        assert not is_error
        assert "file content" in result
        file_manager.read_file.assert_called_once_with("/test/file.txt", None, None)

    def test_write_file(self):
        """Test writing a file."""
        file_manager = Mock()
        file_manager.write_file.return_value = ("File written", False)

        handler = WriteActionHandler(file_manager)
        action = WriteAction(file_path="/test/file.txt", content="new content")

        result, is_error = handler.handle(action)

        assert not is_error
        file_manager.write_file.assert_called_once_with("/test/file.txt", "new content")

    def test_edit_file(self):
        """Test editing a file."""
        file_manager = Mock()
        file_manager.edit_file.return_value = ("File edited", False)

        handler = EditActionHandler(file_manager)
        action = EditAction(
            file_path="/test/file.txt",
            old_string="old",
            new_string="new",
            replace_all=False
        )

        result, is_error = handler.handle(action)

        assert not is_error
        file_manager.edit_file.assert_called_once_with("/test/file.txt", "old", "new", False)


class TestSearchHandlers:
    """Test search operation handlers."""

    def test_grep(self):
        """Test grep search."""
        search_manager = Mock()
        search_manager.grep.return_value = ("match found", False)

        handler = GrepActionHandler(search_manager)
        action = GrepAction(pattern="test", path="/src")

        result, is_error = handler.handle(action)

        assert not is_error
        assert "match found" in result
        search_manager.grep.assert_called_once_with("test", "/src", None)


class TestContextHandler:
    """Test context handler."""

    def test_add_context_success(self):
        """Test adding context successfully."""
        context_store = Mock()
        context_store.add_context.return_value = True
        context_store.get_context.return_value = None

        handler = AddContextActionHandler(context_store)
        action = AddContextAction(id="ctx1", content="context content")

        result, is_error = handler.handle(action)

        assert not is_error
        assert "Added context 'ctx1'" in result

    def test_add_context_duplicate(self):
        """Test adding duplicate context."""
        context_store = Mock()
        context_store.add_context.return_value = False
        context_store.get_context.return_value = Context(id="ctx1", content="context content", reported_by="test")

        handler = AddContextActionHandler(context_store)
        action = AddContextAction(id="ctx1", content="context content")

        result, is_error = handler.handle(action)

        assert is_error
        assert "already exists" in result


class TestReportHandler:
    """Test report handler."""

    def test_report_action(self):
        """Test report action handling."""
        handler = ReportActionHandler()
        action = ReportAction(contexts=[], comments="Test report")

        result, is_error = handler.handle(action)

        assert not is_error
        assert "successful" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


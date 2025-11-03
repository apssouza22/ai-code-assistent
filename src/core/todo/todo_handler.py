"""Todo action handler."""

from typing import Tuple

from src.core.action.actions import BatchTodoAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.common.utils import format_tool_output
from src.core.todo.todo_manager import TodoManager


class BatchTodoActionHandler(ActionHandlerInterface):
  """Handler for batch todo operations."""

  def __init__(self, todo_manager: TodoManager):
    self.todo_manager = todo_manager

  @staticmethod
  def truncate_content(content: str, max_length: int = 15) -> str:
    """Truncate content for display to reduce tokens."""
    return content[:max_length] + "..." if len(content) > max_length else content

  def handle(self, action: BatchTodoAction) -> Tuple[str, bool]:
    """Handle batch todo operations."""
    results = []
    has_error = False

    for op in action.operations:
      if op.action == "add":
        task_id = self.todo_manager.add_task(op.content)
        truncated_content = self.truncate_content(op.content)
        results.append(f"Added todo [{task_id}]: {truncated_content}")

      elif op.action == "complete":
        task = self.todo_manager.get_task(op.task_id)
        if not task:
          results.append(f"[ERROR] Task {op.task_id} not found")
          has_error = True
        elif task["status"] == "completed":
          results.append(f"Task {op.task_id} is already completed")
        else:
          self.todo_manager.complete_task(op.task_id)
          truncated_content = self.truncate_content(task['content'])
          results.append(f"Completed task [{op.task_id}]: {truncated_content}")

      elif op.action == "delete":
        task = self.todo_manager.get_task(op.task_id)
        if not task:
          results.append(f"[ERROR] Task {op.task_id} not found")
          has_error = True
        else:
          self.todo_manager.delete_task(op.task_id)
          truncated_content = self.truncate_content(task['content'])
          results.append(f"Deleted task [{op.task_id}]: {truncated_content}")

      elif op.action == "view_all":
        # This is handled after all operations
        pass

    # Join results
    response = "\n".join(results)

    # Add todo list if requested
    if action.view_all:
      response += f"\n\n{self.todo_manager.view_all()}"

    return format_tool_output("todo", response), has_error

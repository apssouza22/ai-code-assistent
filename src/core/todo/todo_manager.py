from typing import Optional, Dict


class TodoManager:
    """Manages todo list state for agent task tracking."""

    def __init__(self):
        self.todos: Dict[int, Dict[str, str]] = {}
        self.next_id = 1

    def add_task(self, content: str) -> int:
        """Add a new task and return its ID."""
        task_id = self.next_id
        self.todos[task_id] = {"content": content, "status": "pending"}
        self.next_id += 1
        return task_id

    def complete_task(self, task_id: int) -> bool:
        """Mark a task as completed. Returns True if successful."""
        if task_id in self.todos:
            self.todos[task_id]["status"] = "completed"
            return True
        return False

    def delete_task(self, task_id: int) -> bool:
        """Delete a task. Returns True if successful."""
        if task_id in self.todos:
            del self.todos[task_id]
            return True
        return False

    def get_task(self, task_id: int) -> Optional[Dict[str, str]]:
        """Get a specific task by ID."""
        return self.todos.get(task_id)

    def view_all(self) -> str:
        """Return formatted view of all todos."""
        if not self.todos:
            return "Todo list is empty."

        lines = ["Todo List:"]
        for task_id, task in sorted(self.todos.items()):
            status_marker = "[✓]" if task["status"] == "completed" else "[ ]"
            lines.append(f"{status_marker} [{task_id}] {task['content']}")

        return "\n".join(lines)

    def reset(self):
        """Reset the todo manager state."""
        self.todos.clear()
        self.next_id = 1

import logging
from typing import Optional

from src.core.context import ContextStore
from src.core.orchestrator.turn_history import TurnHistory
from src.core.task import TaskStore

logger = logging.getLogger(__name__)


class SessionHistory:
    """Manages the complete state for the orchestrator."""

    def __init__(self, task_store: TaskStore, context_store: ContextStore, turn_history: TurnHistory):
        self.task_store = task_store
        self.context_store = context_store
        self.turn_history = turn_history
        self.done = False
        self.finish_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert orchestrator state to dictionary format."""
        tasks_list = []
        for _, task in self.task_store.tasks.items():
            tasks_list.append(task.to_dict())

        contexts_list = []
        for _, context in self.context_store.get_all_contexts():
            contexts_list.append(context.to_dict())

        return {
            "done": self.done,
            "finish_message": self.finish_message,
            "tasks": tasks_list,
            "context_store": contexts_list,
            "conversation_history": self.turn_history.to_dict()
        }

    def to_prompt(self) -> str:
        """Convert complete state to prompt format for LLM."""
        sections = []

        # Add task manager state
        sections.append("## Task Manager State\n")
        sections.append(self.task_store.task_summary())
        sections.append("\n## Context Store\n")
        sections.append(self._get_context_summary())

        # Add conversation history
        sections.append("\n## Conversation History\n")
        sections.append(self.turn_history.to_prompt())

        return "\n".join(sections)

    def _get_context_summary(self) -> str:
        """Return formatted summary of all stored contexts."""
        if not self.context_store.get_all_contexts():
            return "Context store is empty."

        lines = ["Context Store:"]
        for context_id, context in self.context_store.get_all_contexts():
            lines.append(f"  Id: [{context_id}]")
            lines.append(f"  Content: {context.content}")
            lines.append(f"  Reported by: {context.reported_by}")
        return "\n".join(lines)

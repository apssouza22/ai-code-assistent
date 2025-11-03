import logging
from typing import (
    Dict,
    Any,
)

from src.core.action import TaskCreateAction
from src.core.agent import SubagentReport
from src.core.context import ContextStore, Context
from src.core.task.task import Task, TaskStatus
from src.core.task.task_store import TaskStore

logger = logging.getLogger(__name__)


class TaskManager:
    """Manage task lifecycle and orchestrate subagent execution."""

    def __init__(
        self,
        task_store: TaskStore,
        context_store: ContextStore,
    ):
        self.context_store = context_store

        self.task_store = task_store
        self.task_trajectories: Dict[str, Dict[str, Any]] = {}

    def create_task(self, action: TaskCreateAction) -> Task:
        """Create a task and optionally launch the matching subagent."""
        logger.info(f"Creating task: {action.title}")
        return self.task_store.create_task(
            agent_name=action.agent_name,
            title=action.title,
            description=action.description,
            context_refs=action.context_refs,
            context_bootstrap=action.context_bootstrap,
        )


    def process_task_result(
        self,
        task: Task,
        report: SubagentReport
    ) -> Dict[str, Any]:
        """Process subagent output and extract contexts.
        Args:
            task: The task that was executed
            report: Raw output from subagent containing contexts and comments
        """

        ids = self._persist_contexts(report, task)
        result = {
            'task_id': task.task_id,
            'context_ids_stored': ids,
            'comments': report.comments
        }

        task.result = result
        self.task_store.update_task_status(task.task_id, TaskStatus.COMPLETED)
        if report.meta:
            self.task_trajectories[task.task_id] = {
                "agent_name": task.agent_name,
                "title": task.title,
                "trajectory": report.meta.trajectory if report.meta.trajectory else None,
                "total_input_tokens": report.meta.total_input_tokens,
                "total_output_tokens": report.meta.total_output_tokens,
            }
        return result

    def _persist_contexts(self, report, task: Task) -> list:
        stored_context_ids = []
        for ctx in report.contexts:
            if ctx.id and ctx.content:
                self._add_context(
                    context_id=ctx.id,
                    content=ctx.content,
                    reported_by=task.task_id,
                    task_id=task.task_id
                )
                stored_context_ids.append(ctx.id)
        return stored_context_ids

    def get_and_clear_task_trajectories(self) -> Dict[str, Dict[str, Any]]:
        """Get collected subagent trajectories and clear the internal store."""
        trajectories = self.task_trajectories.copy()
        self.task_trajectories.clear()
        return trajectories

    def get_task(self, task_id) -> Task | None:
        """Retrieve a task by its ID."""
        return self.task_store.get_task(task_id)

    def _add_context(
        self,
        context_id: str,
        content: str,
        reported_by: str,
        task_id: str | None = None
    ) -> bool:
        """Add a context to the context store."""
        if self.context_store.get_context(context_id):
            logger.warning(f"Context {context_id} already exists")
            return False

        context = Context(
            id=context_id,
            content=content,
            reported_by=reported_by,
            task_id=task_id
        )

        self.context_store.add_context(context_id, context)
        logger.info(f"Added context {context_id} to store")
        return True


def create_task_manager(task_store: TaskStore, context_store: ContextStore) -> TaskManager:
    """Factory for creating a TaskManager with pre-configured subagents.
    """
    return TaskManager(
        task_store=task_store,
        context_store=context_store,
    )

"""Context action handler."""
import logging
from typing import Tuple

from src.core.action.actions import AddContextAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.common.utils import format_tool_output
from src.core.context import ContextStore, Context

logger = logging.getLogger(__name__)
class AddContextActionHandler(ActionHandlerInterface):
    """Handler for adding context to store."""

    def __init__(self, context_store: ContextStore):
        self.context_store = context_store

    def handle(self, action: AddContextAction) -> Tuple[str, bool]:
        """Handle adding context to store."""
        try:
            if self.context_store.get_context(action.id):
                logger.warning(f"Context {action.id} already exists")
                response = f"[WARNING] Context '{action.id}' already exists in store"
                return format_tool_output("context", response), True

            context = Context(
                id=action.id,
                content=action.content,
                reported_by=action.reported_by,
                task_id=action.task_id
            )

            self.context_store.add_context(context.id, context)
            logger.info(f"Added context {context.id} to store")
            response = f"Added context '{action.id}' to store"
            return format_tool_output("context", response), False

        except Exception as e:
            error_msg = f"[ERROR] Failed to add context: {str(e)}"
            return format_tool_output("context", error_msg), True


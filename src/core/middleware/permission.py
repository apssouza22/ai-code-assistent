"""Permission middleware — rejects disallowed action types."""

from typing import Set, Type

from src.core.action.actions import Action
from src.core.common.utils import format_tool_output
from src.core.middleware.base import Middleware, ActionCallContext
from src.misc import pretty_log


class PermissionMiddleware(Middleware):
    """Rejects action types not in the allowed set (before_action_call)."""

    def __init__(self, allowed_actions: Set[Type[Action]], agent_name: str = "agent"):
        self._allowed = allowed_actions
        self._agent_name = agent_name

    def before_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        if type(ctx.action) not in self._allowed:
            action_name = type(ctx.action).__name__
            msg = (
                f"[PERMISSION DENIED] {self._agent_name} agent is not allowed "
                f"to execute {action_name}."
            )
            pretty_log.warning(msg, self._agent_name.upper())
            ctx.output = format_tool_output("permission", msg)
            ctx.is_error = True
            ctx.skipped = True
        return ctx

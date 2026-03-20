"""Audit log middleware — structured logging for every action."""

from src.core.action.actions import BashAction
from src.core.middleware.base import Middleware, ActionCallContext
from src.misc import pretty_log


class AuditLogMiddleware(Middleware):
    """Structured audit logging for every action (before + after action_call)."""

    def __init__(self, agent_name: str = "agent"):
        self._agent_name = agent_name

    def before_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        action_name = type(ctx.action).__name__
        pretty_log.debug(f"Executing {action_name}", self._agent_name.upper())
        if isinstance(ctx.action, BashAction):
            pretty_log.debug(f"Command: {ctx.action.cmd}", self._agent_name.upper())
        return ctx

    def after_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        action_name = type(ctx.action).__name__
        status = "ERROR" if ctx.is_error else "OK"
        output_len = len(ctx.output) if ctx.output else 0
        pretty_log.debug(
            f"[AUDIT] agent={self._agent_name} action={action_name} "
            f"status={status} output_len={output_len}",
            self._agent_name.upper()
        )
        return ctx

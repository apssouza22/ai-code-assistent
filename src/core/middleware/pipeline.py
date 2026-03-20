"""Middleware pipeline that drives lifecycle events across a list of middlewares."""

from typing import List, Optional, Tuple, Callable

from src.core.action.actions import Action
from src.core.middleware.base import (
    Middleware, TurnContext, ActionCallContext, ActionCall,
)


class MiddlewarePipeline:
    """Drives the four lifecycle events across a list of middlewares.

    * ``before_*`` hooks run in list order.
    * ``after_*`` hooks run in reverse order (matching chain-of-responsibility
      unwinding semantics).
    * Only middlewares whose ``before_*`` was called (and did not short-circuit)
      will have their ``after_*`` called.
    """

    def __init__(self, middlewares: Optional[List[Middleware]] = None):
        self._middlewares = list(middlewares or [])

    def execute_turn(self, ctx: TurnContext, core_fn: Callable[[TurnContext], TurnContext]) -> TurnContext:
        called = []
        for mw in self._middlewares:
            ctx = mw.before_turn(ctx)
            if ctx.aborted:
                for after_mw in reversed(called):
                    ctx = after_mw.after_turn(ctx)
                return ctx
            called.append(mw)

        try:
            ctx = core_fn(ctx)
        except Exception as exc:
            ctx.metadata["turn_exception"] = exc

        for mw in reversed(called):
            ctx = mw.after_turn(ctx)

        return ctx

    def execute_action(self, action: Action, handler: ActionCall, agent_name: str = "") -> Tuple[str, bool]:
        ctx = ActionCallContext(action=action, agent_name=agent_name)

        called = []
        for mw in self._middlewares:
            ctx = mw.before_action_call(ctx)
            if ctx.skipped:
                for after_mw in reversed(called):
                    ctx = after_mw.after_action_call(ctx)
                return ctx.output, ctx.is_error
            called.append(mw)

        ctx.output, ctx.is_error = handler(action)

        for mw in reversed(called):
            ctx = mw.after_action_call(ctx)

        return ctx.output, ctx.is_error

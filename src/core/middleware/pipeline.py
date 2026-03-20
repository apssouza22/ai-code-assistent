"""Middleware pipeline that drives lifecycle events across a list of middlewares."""

from typing import Any, Dict, List, Optional, Tuple, Callable

from src.core.action.actions import Action
from src.core.middleware.base import (
    Middleware, TurnContext, ModelCallContext, ActionCallContext, ActionCall, ModelCall,
)


class MiddlewarePipeline:
    """Drives the six lifecycle events across a list of middlewares.

    * ``before_*`` hooks run in list order.
    * ``after_*`` hooks run in reverse order (matching chain-of-responsibility
      unwinding semantics).
    * Only middlewares whose ``before_*`` was called (and did not short-circuit)
      will have their ``after_*`` called.
    """

    def __init__(self, middlewares: Optional[List[Middleware]] = None):
        self._middlewares = list(middlewares or [])

    # -- Turn lifecycle -----------------------------------------------------

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

    # -- Model-call lifecycle -----------------------------------------------

    def execute_model_call(
        self,
        messages: List[Dict[str, Any]],
        model_fn: ModelCall,
        agent_name: str = "",
    ) -> ModelCallContext:
        ctx = ModelCallContext(messages=messages, agent_name=agent_name)

        called = []
        for mw in self._middlewares:
            ctx = mw.before_model_call(ctx)
            if ctx.skipped:
                for after_mw in reversed(called):
                    ctx = after_mw.after_model_call(ctx)
                return ctx
            called.append(mw)

        ctx.response = model_fn(ctx.messages)

        for mw in reversed(called):
            ctx = mw.after_model_call(ctx)

        return ctx

    # -- Action lifecycle ---------------------------------------------------

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

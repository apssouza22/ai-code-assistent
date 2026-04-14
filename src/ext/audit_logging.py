"""Turn logging middleware — structured logging before and after each turn."""

import time

from src.core.action.actions import BashAction
from src.core.middleware import ActionCallContext
from src.core.middleware.base import Middleware, TurnContext, ModelCallContext
from src.misc import pretty_log


class LoggingMiddleware(Middleware):
    """Structured logging before and after each turn."""

    def before_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        pretty_log.info(f"Executing action: {type(ctx.action).__name__} - {ctx.action}", ctx.agent_name.upper())
        if isinstance(ctx.action, BashAction):
            pretty_log.info(f"Executing bash command: {ctx.action.cmd}", ctx.agent_name.upper())
        return ctx

    def before_turn(self, ctx: TurnContext) -> TurnContext:
        pretty_log.info(f"Turn {ctx.turn_num}/{ctx.max_turns} starting", ctx.agent_name.upper())
        ctx.metadata["_turn_start"] = time.time()
        return ctx

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        agent = ctx.agent_name.upper()
        start = ctx.metadata.pop("_turn_start", None)
        elapsed = time.time() - start if start else 0
        ctx.metadata["turn_duration_secs"] = round(elapsed, 2)

        if ctx.aborted:
            pretty_log.warning(f"Turn {ctx.turn_num} aborted: {ctx.abort_reason}", agent)
            return ctx

        if ctx.result and ctx.result.done:
            pretty_log.success(
                f"Turn {ctx.turn_num} finished task - {ctx.result.finish_message}", agent
            )
            return ctx

        actions_count = len(ctx.result.actions_executed) if ctx.result else 0
        has_error = ctx.result.has_error if ctx.result else False
        pretty_log.debug(
            f"Turn {ctx.turn_num} complete in {elapsed:.2f}s "
            f"({actions_count} actions, error={has_error})",
            agent,
        )

        return ctx

"""Turn logging middleware — structured logging before and after each turn."""

import time

from src.core.middleware.base import Middleware, TurnContext
from src.misc import pretty_log


class TurnLoggingMiddleware(Middleware):
    """Structured logging before and after each turn."""

    def before_turn(self, ctx: TurnContext) -> TurnContext:
        agent = ctx.agent_name.upper()
        pretty_log.info(f"Turn {ctx.turn_num}/{ctx.max_turns} starting", agent)
        ctx.metadata["_turn_start"] = time.time()
        return ctx

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        agent = ctx.agent_name.upper()
        start = ctx.metadata.pop("_turn_start", None)
        elapsed = time.time() - start if start else 0
        ctx.metadata["turn_duration_secs"] = round(elapsed, 2)

        if ctx.aborted:
            pretty_log.warning(f"Turn {ctx.turn_num} aborted: {ctx.abort_reason}", agent)
        elif ctx.result and ctx.result.done:
            pretty_log.success(
                f"Turn {ctx.turn_num} finished task - {ctx.result.finish_message}", agent
            )
        else:
            actions_count = len(ctx.result.actions_executed) if ctx.result else 0
            has_error = ctx.result.has_error if ctx.result else False
            pretty_log.debug(
                f"Turn {ctx.turn_num} complete in {elapsed:.2f}s "
                f"({actions_count} actions, error={has_error})",
                agent,
            )

        return ctx

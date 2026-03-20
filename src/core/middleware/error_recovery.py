"""Error recovery middleware — converts unhandled turn exceptions into error results."""

import logging

from src.core.action.actions_result import ExecutionResult
from src.core.middleware.base import Middleware, TurnContext
from src.misc import pretty_log

logger = logging.getLogger(__name__)


class ErrorRecoveryMiddleware(Middleware):
    """Converts unhandled turn exceptions into an error ExecutionResult (after_turn)."""

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        exc = ctx.metadata.pop("turn_exception", None)
        if exc is not None:
            agent = ctx.agent_name.upper()
            pretty_log.error(f"Error in turn {ctx.turn_num}: {exc}", agent)
            logger.error(
                f"Turn {ctx.turn_num} error for {ctx.agent_name}", exc_info=exc
            )

            ctx.result = ExecutionResult(
                actions_executed=[],
                env_responses=[f"[ERROR] Turn failed: {str(exc)}"],
                has_error=True,
                done=False,
            )
            ctx.metadata["turn_error"] = str(exc)

        return ctx

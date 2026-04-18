"""Error recovery middleware — converts unhandled turn exceptions into error results."""

from src.core.action.actions_result import ExecutionResult
from src.core.middleware.base import Middleware, TurnContext
from src.misc import pretty_log
import  traceback

class ErrorRecoveryMiddleware(Middleware):
    """Converts unhandled turn exceptions into an error ExecutionResult (after_turn)."""

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        exc = ctx.turn_exception
        if exc is not None:
            agent = ctx.agent_name.upper()
            pretty_log.error(f"Error in turn {ctx.turn_num}: Stacktrace :  {traceback.print_stack(exc)}", agent)
            pretty_log.error(
                f"Turn {ctx.turn_num} error for {ctx.agent_name}", exc_info=exc
            )

            ctx.result = ExecutionResult(
                actions_executed=[],
                actions_outputs=[f"[ERROR] Turn failed: {str(exc)}"],
                has_error=True,
                done=False,
            )
            ctx.metadata["turn_error"] = str(exc)

        return ctx

"""Turn file logging middleware — writes structured turn data to a file logger."""

from src.core.middleware.base import Middleware, TurnContext
from src.misc import TurnLogger


class TurnFileLoggingMiddleware(Middleware):
    """Writes structured turn data to a file logger after each turn.

    Builds a log payload from common ``TurnContext`` fields (LLM response,
    execution result) plus any non-private metadata.  Metadata keys that
    start with ``_`` are treated as internal and excluded from the log.

    Should be placed first in the middleware list so its ``after_turn``
    executes last (after error-recovery, timing, etc. have enriched the
    context).
    """

    def __init__(self, turn_logger: TurnLogger):
        self._turn_logger = turn_logger

    @property
    def turn_logger(self) -> TurnLogger:
        return self._turn_logger

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        if not self._turn_logger or not self._turn_logger.enabled or not ctx.result:
            return ctx

        result = ctx.result
        turn_data = {
            "agent_name": ctx.agent_name,
            "llm_response": ctx.llm_response,
            "actions_executed": [str(a) for a in result.actions_executed],
            "env_responses": result.env_responses,
            "done": result.done,
            "has_error": result.has_error,
            "finish_message": result.finish_message,
            "task_trajectories": result.task_trajectories,
        }

        for k, v in ctx.metadata.items():
            if not k.startswith("_") and k not in turn_data:
                turn_data[k] = v

        self._turn_logger.log_turn(ctx.turn_num, turn_data)
        return ctx

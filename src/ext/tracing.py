"""Turn file logging middleware — writes structured turn data to a file logger."""

from pathlib import Path
from typing import Optional

from src.core.middleware.base import Middleware, TurnContext
from src.misc import TurnLogger


class TracingMiddleware(Middleware):
    """Writes structured turn data to a file logger after each turn.

    Builds a log payload from common ``TurnContext`` fields (LLM response,
    execution result) plus any non-private metadata.  Metadata keys that
    start with ``_`` are treated as internal and excluded from the log.

    ``TurnLogger`` is created per turn using ``ctx.turn_log_prefix`` or
    ``ctx.agent_name`` as the file prefix.

    Should be placed last in the middleware list so its ``after_turn``
    runs after error-recovery, output truncation, etc. have enriched the
    context.
    """

    def __init__(self, logging_dir: Optional[Path] = None):
        self._logging_dir = logging_dir

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        prefix = ctx.turn_log_prefix or ctx.agent_name
        turn_logger = TurnLogger(self._logging_dir, prefix)
        if not turn_logger.enabled or not ctx.result:
            return ctx

        result = ctx.result
        turn_data = {
            "agent_name": ctx.agent_name,
            "llm_response": ctx.llm_response,
            "actions_executed": [str(a) for a in result.actions_executed],
            "env_responses": result.actions_outputs,
            "done": result.done,
            "has_error": result.has_error,
            "finish_message": result.finish_message,
            "task_trajectories": result.task_trajectories,
        }

        for k, v in ctx.metadata.items():
            if not k.startswith("_") and k not in turn_data:
                turn_data[k] = v

        turn_logger.log_turn(ctx.turn_num, turn_data)
        return ctx

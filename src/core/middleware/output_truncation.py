"""Output truncation middleware — trims oversized action output."""

from src.core.middleware.base import Middleware, ActionCallContext


class OutputTruncationMiddleware(Middleware):
    """Truncates action output that exceeds a character limit (after_action_call)."""

    TRUNCATION_NOTICE = "\n... [OUTPUT TRUNCATED — {removed} chars removed, {total} total] ..."

    def __init__(self, max_chars: int = 30_000):
        self._max_chars = max_chars

    def after_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        if ctx.output and len(ctx.output) > self._max_chars:
            total = len(ctx.output)
            removed = total - self._max_chars
            ctx.output = ctx.output[: self._max_chars] + self.TRUNCATION_NOTICE.format(
                removed=removed, total=total
            )
        return ctx

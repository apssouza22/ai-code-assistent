"""Token budget middleware — aborts the turn when history exceeds a token limit."""

from typing import Optional

from src.core.middleware.base import Middleware, TurnContext
from src.core.llm import count_tokens_for_messages
from src.misc import pretty_log


class TokenBudgetMiddleware(Middleware):
    """Aborts the turn if message history exceeds a token budget (before_turn)."""

    def __init__(self, max_tokens: int, model: Optional[str] = None):
        self._max_tokens = max_tokens
        self._model = model

    def before_turn(self, ctx: TurnContext) -> TurnContext:
        model = self._model or "gpt-5"
        token_count = count_tokens_for_messages(ctx.messages, model)
        ctx.metadata["pre_turn_token_count"] = token_count

        if token_count > self._max_tokens:
            ctx.aborted = True
            ctx.abort_reason = (
                f"Token budget exceeded: {token_count} > {self._max_tokens}"
            )
            pretty_log.warning(ctx.abort_reason, ctx.agent_name.upper())

        return ctx

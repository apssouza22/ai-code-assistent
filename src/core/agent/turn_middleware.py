"""Turn-level middleware for agent execution pipelines.

Middlewares wrap the core turn execution (LLM call -> action parse -> execute)
with cross-cutting concerns like logging, token budgets, and error recovery.
"""

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.core.agent.actions_result import ExecutionResult
from src.core.llm import count_tokens_for_messages
from src.misc import pretty_log

logger = logging.getLogger(__name__)


@dataclass
class TurnContext:
    """Shared state passed through the middleware chain for a single turn."""
    agent_name: str
    turn_num: int
    max_turns: int
    messages: List[Dict[str, str]]
    llm_response: Optional[str] = None
    result: Optional[ExecutionResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    aborted: bool = False
    abort_reason: Optional[str] = None


class TurnMiddleware(ABC):
    """Base class for turn-level middleware.

    Each middleware receives a TurnContext and a `next_call` function.
    It can inspect/modify the context before calling next_call (pre-processing),
    and inspect/modify it after (post-processing), or skip next_call entirely
    to abort the turn.
    """

    @abstractmethod
    def __call__(self, ctx: TurnContext, next_call) -> TurnContext:
        ...


class TurnPipeline:
    """Composes a list of TurnMiddleware into a single callable chain."""

    def __init__(self, middlewares: List[TurnMiddleware]):
        self._middlewares = list(middlewares)

    def execute(self, ctx: TurnContext, core_fn) -> TurnContext:
        """Run the middleware chain around `core_fn`.

        Args:
            ctx: The turn context to thread through.
            core_fn: The actual turn logic — callable(TurnContext) -> TurnContext.
        """
        chain = core_fn
        for mw in reversed(self._middlewares):
            prev = chain
            chain = lambda c, _mw=mw, _prev=prev: _mw(c, _prev)
        return chain(ctx)


class TurnLoggingMiddleware(TurnMiddleware):
    """Structured logging before and after each turn."""

    def __call__(self, ctx: TurnContext, next_call) -> TurnContext:
        agent = ctx.agent_name.upper()
        pretty_log.info(f"Turn {ctx.turn_num}/{ctx.max_turns} starting", agent)
        start = time.time()

        ctx = next_call(ctx)

        elapsed = time.time() - start
        ctx.metadata["turn_duration_secs"] = round(elapsed, 2)

        if ctx.aborted:
            pretty_log.warning(f"Turn {ctx.turn_num} aborted: {ctx.abort_reason}", agent)
        elif ctx.result and ctx.result.done:
            pretty_log.success(f"Turn {ctx.turn_num} finished task - {ctx.result.finish_message}", agent)
        else:
            actions_count = len(ctx.result.actions_executed) if ctx.result else 0
            has_error = ctx.result.has_error if ctx.result else False
            pretty_log.debug(
                f"Turn {ctx.turn_num} complete in {elapsed:.2f}s "
                f"({actions_count} actions, error={has_error})",
                agent,
            )

        return ctx


class TokenBudgetMiddleware(TurnMiddleware):
    """Aborts the turn if the message history exceeds a token budget.

    This prevents sending requests that are too large for the model context
    window and helps control costs.
    """

    def __init__(self, max_tokens: int, model: Optional[str] = None):
        self._max_tokens = max_tokens
        self._model = model

    def __call__(self, ctx: TurnContext, next_call) -> TurnContext:
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

        return next_call(ctx)


class ErrorRecoveryMiddleware(TurnMiddleware):
    """Catches exceptions during turn execution and converts them to
    a failed ExecutionResult instead of crashing the agent loop."""

    def __call__(self, ctx: TurnContext, next_call) -> TurnContext:
        try:
            return next_call(ctx)
        except Exception as e:
            agent = ctx.agent_name.upper()
            pretty_log.error(f"Error in turn {ctx.turn_num}: {e}", agent)
            logger.exception(f"Turn {ctx.turn_num} error for {ctx.agent_name}")

            ctx.result = ExecutionResult(
                actions_executed=[],
                env_responses=[f"[ERROR] Turn failed: {str(e)}"],
                has_error=True,
                done=False,
            )
            ctx.metadata["turn_error"] = str(e)
            return ctx

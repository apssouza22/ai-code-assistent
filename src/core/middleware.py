"""Unified event-based middleware for agent execution pipelines.

A single Middleware type handles cross-cutting concerns at both the turn
and action levels through four lifecycle events:

  before_turn        – runs before each turn (can abort)
  after_turn         – runs after each turn completes (or fails/aborts)
  before_action_call – runs before each action dispatch (can skip)
  after_action_call  – runs after each action dispatch completes
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable, Set, Type

from src.core.action.actions import Action, BashAction
from src.core.agent.actions_result import ExecutionResult
from src.core.common.utils import format_tool_output
from src.core.llm import count_tokens_for_messages
from src.misc import pretty_log, TurnLogger

logger = logging.getLogger(__name__)

ActionCall = Callable[[Action], Tuple[str, bool]]


# ---------------------------------------------------------------------------
# Contexts
# ---------------------------------------------------------------------------

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


@dataclass
class ActionCallContext:
    """Shared state passed through the middleware chain for a single action."""
    action: Action
    agent_name: str = ""
    output: Optional[str] = None
    is_error: bool = False
    skipped: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base Middleware
# ---------------------------------------------------------------------------

class Middleware:
    """Unified middleware base class with event-based hooks.

    Override only the events you care about; defaults are no-ops.
    """

    def before_turn(self, ctx: TurnContext) -> TurnContext:
        """Called before each turn. Set ``ctx.aborted = True`` to skip the turn."""
        return ctx

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        """Called after each turn completes (including aborts and errors)."""
        return ctx

    def before_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        """Called before each action. Set ``ctx.skipped = True`` to skip execution."""
        return ctx

    def after_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        """Called after each action execution completes."""
        return ctx


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class MiddlewarePipeline:
    """Drives the four lifecycle events across a list of middlewares.

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


# ---------------------------------------------------------------------------
# Concrete middlewares — Action events
# ---------------------------------------------------------------------------

class PermissionMiddleware(Middleware):
    """Rejects action types not in the allowed set (before_action_call)."""

    def __init__(self, allowed_actions: Set[Type[Action]], agent_name: str = "agent"):
        self._allowed = allowed_actions
        self._agent_name = agent_name

    def before_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        if type(ctx.action) not in self._allowed:
            action_name = type(ctx.action).__name__
            msg = (
                f"[PERMISSION DENIED] {self._agent_name} agent is not allowed "
                f"to execute {action_name}."
            )
            pretty_log.warning(msg, self._agent_name.upper())
            ctx.output = format_tool_output("permission", msg)
            ctx.is_error = True
            ctx.skipped = True
        return ctx


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


class TimingMiddleware(Middleware):
    """Logs per-action execution time (before + after action_call)."""

    def before_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        ctx.metadata["_timing_start"] = time.time()
        return ctx

    def after_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        start = ctx.metadata.pop("_timing_start", None)
        if start is not None:
            elapsed = time.time() - start
            action_name = type(ctx.action).__name__
            if elapsed > 5.0:
                pretty_log.info(f"{action_name} took {elapsed:.2f}s", "ACTION_TIMING")
            else:
                logger.debug(f"{action_name} completed in {elapsed:.2f}s")
        return ctx


class AuditLogMiddleware(Middleware):
    """Structured audit logging for every action (before + after action_call)."""

    def __init__(self, agent_name: str = "agent"):
        self._agent_name = agent_name

    def before_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        action_name = type(ctx.action).__name__
        pretty_log.debug(f"Executing {action_name}", self._agent_name.upper())
        if isinstance(ctx.action, BashAction):
            pretty_log.debug(f"Command: {ctx.action.cmd}", self._agent_name.upper())
        return ctx

    def after_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        action_name = type(ctx.action).__name__
        status = "ERROR" if ctx.is_error else "OK"
        output_len = len(ctx.output) if ctx.output else 0
        pretty_log.warning(
            f"[AUDIT] agent={self._agent_name} action={action_name} "
            f"status={status} output_len={output_len}",
            self._agent_name.upper()
        )
        return ctx


# ---------------------------------------------------------------------------
# Concrete middlewares — Turn events
# ---------------------------------------------------------------------------

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

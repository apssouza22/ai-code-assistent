"""Action-level middleware for the action execution pipeline.

Middlewares wrap individual action handler calls with cross-cutting concerns
like permission checks, output truncation, timing, and audit logging.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Callable, List, Set, Type, Optional

from src.core.action.actions import Action
from src.core.common.utils import format_tool_output
from src.misc import pretty_log

logger = logging.getLogger(__name__)

ActionCall = Callable[[Action], Tuple[str, bool]]


class ActionMiddleware(ABC):
    """Base class for action-level middleware.

    Each middleware receives an Action and a `next_call` function that
    represents the rest of the chain (ending with the actual handler).
    It can inspect/modify before calling next_call, inspect/modify the
    result after, or short-circuit by returning early.
    """

    @abstractmethod
    def __call__(self, action: Action, next_call: ActionCall) -> Tuple[str, bool]:
        ...


class ActionPipeline:
    """Composes a list of ActionMiddleware into a single callable chain."""

    def __init__(self, middlewares: Optional[List[ActionMiddleware]] = None):
        self._middlewares = list(middlewares or [])

    def wrap(self, handler: ActionCall) -> ActionCall:
        """Return a new callable that runs `handler` through all middlewares."""
        chain = handler
        for mw in reversed(self._middlewares):
            prev = chain
            chain = lambda action, _mw=mw, _prev=prev: _mw(action, _prev)
        return chain


class PermissionMiddleware(ActionMiddleware):
    """Rejects action types not in the allowed set.

    Provides explicit, descriptive error messages when an agent attempts
    a disallowed action (e.g., explorer trying to write files).
    """

    def __init__(self, allowed_actions: Set[Type[Action]], agent_name: str = "agent"):
        self._allowed = allowed_actions
        self._agent_name = agent_name

    def __call__(self, action: Action, next_call: ActionCall) -> Tuple[str, bool]:
        if type(action) not in self._allowed:
            action_name = type(action).__name__
            msg = (
                f"[PERMISSION DENIED] {self._agent_name} agent is not allowed "
                f"to execute {action_name}."
            )
            pretty_log.warning(msg, self._agent_name.upper())
            return format_tool_output("permission", msg), True

        return next_call(action)


class OutputTruncationMiddleware(ActionMiddleware):
    """Truncates action output that exceeds a character limit.

    Prevents a single action from flooding the LLM context window
    with extremely long outputs (e.g., large file reads, verbose bash output).
    """

    TRUNCATION_NOTICE = "\n... [OUTPUT TRUNCATED — {removed} chars removed, {total} total] ..."

    def __init__(self, max_chars: int = 30_000):
        self._max_chars = max_chars

    def __call__(self, action: Action, next_call: ActionCall) -> Tuple[str, bool]:
        output, is_error = next_call(action)

        if len(output) > self._max_chars:
            total = len(output)
            removed = total - self._max_chars
            output = output[:self._max_chars] + self.TRUNCATION_NOTICE.format(
                removed=removed, total=total
            )

        return output, is_error


class TimingMiddleware(ActionMiddleware):
    """Logs per-action execution time."""

    def __call__(self, action: Action, next_call: ActionCall) -> Tuple[str, bool]:
        action_name = type(action).__name__
        start = time.time()

        output, is_error = next_call(action)

        elapsed = time.time() - start
        if elapsed > 5.0:
            pretty_log.warning(
                f"{action_name} took {elapsed:.2f}s",
                "ACTION_TIMING",
            )
        else:
            logger.debug(f"{action_name} completed in {elapsed:.2f}s")

        return output, is_error


class AuditLogMiddleware(ActionMiddleware):
    """Structured audit logging for every action execution."""

    def __init__(self, agent_name: str = "agent"):
        self._agent_name = agent_name

    def __call__(self, action: Action, next_call: ActionCall) -> Tuple[str, bool]:
        action_name = type(action).__name__
        pretty_log.debug(f"Executing {action_name}", self._agent_name.upper())

        output, is_error = next_call(action)

        status = "ERROR" if is_error else "OK"
        logger.info(
            f"[AUDIT] agent={self._agent_name} action={action_name} status={status} "
            f"output_len={len(output)}"
        )

        return output, is_error

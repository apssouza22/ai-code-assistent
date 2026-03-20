"""Timing middleware — logs per-action execution time."""

import time
import logging

from src.core.middleware.base import Middleware, ActionCallContext
from src.misc import pretty_log

logger = logging.getLogger(__name__)


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

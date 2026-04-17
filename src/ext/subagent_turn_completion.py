"""Subagent turn completion — updates conversation history after each turn."""

from __future__ import annotations

from src.core.middleware.base import Middleware, TurnContext
from src.misc import pretty_log


class SubagentTurnCompletionMiddleware(Middleware):
    """Appends assistant/tool output to ``ctx.messages`` and sets ``metadata['_report']``.

    Register after ``TracingMiddleware`` so trace logs reflect the turn before
    history is extended for the next iteration.
    """

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        if ctx.result is None:
            return ctx

        outputs = "\n".join(ctx.result.actions_outputs)
        pretty_log.debug(f"Action output: {outputs}", ctx.agent_name.upper())

        ctx.messages.append({"role": "assistant", "content": ctx.llm_response})
        ctx.messages.append({"role": "user", "content": outputs})

        if ctx.aborted:
            ctx.messages.append(
                {
                    "role": "user",
                    "content": f"Turn aborted: {ctx.abort_reason}. Please continue.",
                }
            )
            return ctx

        if ctx.metadata.get("turn_error"):
            ctx.messages.append(
                {
                    "role": "user",
                    "content": f"Error occurred: {ctx.metadata['turn_error']}. Please continue.",
                }
            )
            return ctx

        return ctx

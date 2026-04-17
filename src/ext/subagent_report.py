"""Subagent turn completion — updates conversation history after each turn."""

from __future__ import annotations

from src.core.action import ReportAction
from src.core.agent.subagent_report import ContextItem, SubagentReport
from src.core.middleware.base import Middleware, TurnContext
from src.misc import pretty_log


class SubagentReportMiddleware(Middleware):
    """ Build the agent report from the ReportAction """

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        if ctx.result is None:
            return ctx

        for action in ctx.result.actions_executed:
            if isinstance(action, ReportAction):
                pretty_log.info(f"Subagent report comments: {action.comments}", ctx.agent_name.upper())
                contexts = [ContextItem(id=ctx["id"], content=ctx["content"]) for ctx in action.contexts]
                ctx.report =  SubagentReport(
                    contexts=contexts,
                    comments=action.comments,
                )

        return ctx

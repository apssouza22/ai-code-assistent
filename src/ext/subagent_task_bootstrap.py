"""Initialize subagent conversation from task before the first turn."""

from __future__ import annotations

from src.core.middleware.base import AgentTaskContext, Middleware


class SubagentTaskBootstrapMiddleware(Middleware):
    """Sets ``messages`` to system + task user prompt. Register before turn middleware."""

    def before_agent_task(self, ctx: AgentTaskContext) -> AgentTaskContext:
        from src.core.agent.subagent_task import SubagentTask, build_subagent_task_prompt

        if not isinstance(ctx.task, SubagentTask):
            return ctx
        ctx.messages[:] = [
            {"role": "system", "content": ctx.system_message},
            {"role": "user", "content": build_subagent_task_prompt(ctx.task)},
        ]
        return ctx

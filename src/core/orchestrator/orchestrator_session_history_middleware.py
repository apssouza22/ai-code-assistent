"""Orchestrator turn completion — records each turn into session history."""
from src.core.agent.agent_report import AgentReport
from src.core.middleware.base import Middleware, TurnContext
from src.core.orchestrator.session_history import SessionHistory
from src.core.orchestrator.turn import Turn
from src.misc import pretty_log


class OrchestratorSessionHistoryMiddleware(Middleware):
    """Appends the completed turn to ``SessionHistory`` and mirrors ``done`` / ``finish_message``."""

    def __init__(self, session_history: SessionHistory) -> None:
        self._session_history = session_history

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        result = ctx.result
        if result is None:
            return ctx

        turn = Turn(
            llm_output=ctx.llm_response,
            actions_executed=result.actions_executed,
            action_outputs=result.actions_outputs,
            task_trajectories=result.task_trajectories,
        )
        self._session_history.turn_history.add_turn(turn)
        self._session_history.done = result.done
        self._session_history.finish_message = result.finish_message

        if result.done:
            report = {
                'completed': self._session_history.done,
                'finish_message': self._session_history.finish_message,
                'turns_executed': ctx.turn_num,
                'max_turns_reached': ctx.turn_num >= ctx.max_turns
            }
            ctx.report = AgentReport("Orchestrator task completed.", metadata=report)

        if ctx.result is not None:
            pretty_log.debug(f"Action output: {ctx.result.actions_outputs}", "ORCHESTRATOR")

        if ctx.result is not None and ctx.result.done:
            pretty_log.success(f"Task completed: {ctx.result.finish_message}", "ORCHESTRATOR")

        return ctx

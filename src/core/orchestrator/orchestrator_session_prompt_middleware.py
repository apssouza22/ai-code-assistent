"""Orchestrator turn bootstrap — appends system + session-scoped user prompt before each turn."""

from src.core.middleware.base import Middleware, TurnContext
from src.core.orchestrator.session_history import SessionHistory


class OrchestratorSessionPromptMiddleware(Middleware):
    """Appends orchestrator system message and task + session state user message."""

    def __init__(self, session_history: SessionHistory, system_message: str) -> None:
        self._session_history = session_history
        self._system_message = system_message

    def before_turn(self, ctx: TurnContext) -> TurnContext:
        agent_prompt = f"## Current Task\n{ctx.prompt}\n\n{self._session_history.to_prompt()}"
        ctx.messages.append({"role": "system", "content": self._system_message})
        ctx.messages.append({"role": "user", "content": agent_prompt})
        return ctx

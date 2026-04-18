"""Unified event-based middleware for agent execution pipelines."""

from src.core.middleware.base import (
    Middleware,
    AgentTaskContext,
    TurnContext,
    ModelCallContext,
    ActionCallContext,
    ActionCall,
    ModelCall,
)
from src.core.middleware.pipeline import MiddlewarePipeline
from src.ext.output_truncation import ActionOutputTruncationMiddleware
from src.ext.audit_logging import LoggingMiddleware
from src.ext.error_recovery import ErrorRecoveryMiddleware
from src.ext.tracing import TracingMiddleware
from src.ext.subagent_turn_completion import SubagentTurnCompletionMiddleware
from src.ext.subagent_task_bootstrap import SubagentTaskBootstrapMiddleware
from src.core.action.action_handler_middleware import ActionHandlerMiddleware

__all__ = [
    "Middleware",
    "AgentTaskContext",
    "TurnContext",
    "ModelCallContext",
    "ActionCallContext",
    "ActionCall",
    "ModelCall",
    "MiddlewarePipeline",
    "ActionOutputTruncationMiddleware",
    "LoggingMiddleware",
    "ErrorRecoveryMiddleware",
    "TracingMiddleware",
    "SubagentTurnCompletionMiddleware",
    "SubagentTaskBootstrapMiddleware",
    "ActionHandlerMiddleware",
]

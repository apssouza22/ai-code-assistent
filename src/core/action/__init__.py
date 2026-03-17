"""
Action module - Public API for actions, handlers, and parsing.

This module provides a clean boundary for the action subsystem by exposing
only the classes and functions needed by external modules.
"""
from src.core.action.actions import (
    Action,
    FinishAction,
    TaskCreateAction,
    ReportAction,
)

from src.core.action.parser import SimpleActionParser
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.action.middleware import (
    ActionMiddleware,
    ActionPipeline,
    PermissionMiddleware,
    OutputTruncationMiddleware,
    TimingMiddleware,
    AuditLogMiddleware,
)


__all__ = [
    "Action",
    "FinishAction",
    "TaskCreateAction",
    "ReportAction",
    "SimpleActionParser",
    "ActionHandlerInterface",
    "ActionMiddleware",
    "ActionPipeline",
    "PermissionMiddleware",
    "OutputTruncationMiddleware",
    "TimingMiddleware",
    "AuditLogMiddleware",
]


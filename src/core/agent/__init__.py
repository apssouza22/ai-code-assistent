"""
Agent module - Public API for agents, tasks, and execution results.

This module provides a clean boundary for the agent subsystem by exposing
only the classes and functions needed by external modules.
"""
from src.core.agent.agent import Agent, AgentTask
from src.core.agent.subagent_task import SubagentTask
from src.core.agent.subagent_report import SubagentReport, ContextItem, ReportMetadata
from src.core.action.actions_result import ExecutionResult

__all__ = [
    "Agent",
    "AgentTask",
    "SubagentTask",
    "SubagentReport",
    "ContextItem",
    "ReportMetadata",
    "ExecutionResult",
]

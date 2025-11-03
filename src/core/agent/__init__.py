"""
Agent module - Public API for agents, tasks, and execution results.

This module provides a clean boundary for the agent subsystem by exposing
only the classes and functions needed by external modules.
"""
from src.core.agent.agent import Agent, AgentTask
from src.core.agent.subagent import Subagent, SubagentTask
from src.core.agent.subagent_report import SubagentReport, ContextItem, SubagentMeta
from src.core.agent.agent_manager import AgentManager
from src.core.agent.actions_result import ExecutionResult

__all__ = [
    "Agent",
    "AgentTask",
    "Subagent",
    "SubagentTask",
    "SubagentReport",
    "ContextItem",
    "SubagentMeta",
    "AgentManager",
    "ExecutionResult",
]


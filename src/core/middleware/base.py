"""Base middleware class and shared context types.

A single Middleware type handles cross-cutting concerns at the task, turn,
model-call, and action levels through lifecycle events:

  before_agent_task  – runs before the agent task body (can abort)
  after_agent_task   – runs after the task body (success or exception)
  before_turn        – runs before each turn (can abort)
  after_turn         – runs after each turn completes (or fails/aborts)
  before_model_call  – runs before each LLM call (can skip with a cached response)
  after_model_call   – runs after each LLM call completes
  before_action_call – runs before each action dispatch (can skip)
  after_action_call  – runs after each action dispatch completes
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable

from src.core.action.actions import Action
from src.core.action.actions_result import ExecutionResult
from src.core.agent.subagent_report import SubagentReport

ActionCall = Callable[[Action], Tuple[str, bool]]
ModelCall = Callable[[List[Dict[str, Any]]], str]


@dataclass
class AgentTaskContext:
    """State for middleware around a single ``run_task`` / agent-task execution."""
    task: Any
    agent_name: str
    system_message: str
    messages: List[Dict[str, str]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    aborted: bool = False
    abort_reason: Optional[str] = None
    task_result: Any = None
    task_exception: Optional[BaseException] = None


@dataclass
class TurnContext:
    """Shared state passed through the middleware chain for a single turn."""
    agent_name: str
    turn_num: int
    max_turns: int
    prompt: str
    messages: List[Dict[str, str]]
    llm_response: Optional[str] = None
    result: Optional[ExecutionResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    aborted: bool = False
    abort_reason: Optional[str] = None
    turn_log_prefix: Optional[str] = None
    report: Optional[SubagentReport] = None
    turn_exception: Optional[BaseException] = None


@dataclass
class ModelCallContext:
    """Shared state passed through the middleware chain for a single LLM call."""
    messages: List[Dict[str, Any]]
    agent_name: str = ""
    response: Optional[str] = None
    skipped: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionCallContext:
    """Shared state passed through the middleware chain for a single action."""
    action: Action
    agent_name: str = ""
    output: Optional[str] = None
    is_error: bool = False
    skipped: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class Middleware:
    """Unified middleware base class with event-based hooks.

    Override only the events you care about; defaults are no-ops.
    """

    def before_agent_task(self, ctx: AgentTaskContext) -> AgentTaskContext:
        """Called before the task body. Set ``ctx.aborted = True`` to skip the task."""
        return ctx

    def after_agent_task(self, ctx: AgentTaskContext) -> AgentTaskContext:
        """Called after the task body (including when ``ctx.aborted`` before the body)."""
        return ctx

    def before_turn(self, ctx: TurnContext) -> TurnContext:
        """Called before each turn. Set ``ctx.aborted = True`` to skip the turn."""
        return ctx

    def after_turn(self, ctx: TurnContext) -> TurnContext:
        """Called after each turn completes (including aborts and errors)."""
        return ctx

    def before_model_call(self, ctx: ModelCallContext) -> ModelCallContext:
        """Called before each LLM call. Set ``ctx.skipped = True`` to skip the call."""
        return ctx

    def after_model_call(self, ctx: ModelCallContext) -> ModelCallContext:
        """Called after each LLM call completes."""
        return ctx

    def before_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        """Called before each action. Set ``ctx.skipped = True`` to skip execution."""
        return ctx

    def after_action_call(self, ctx: ActionCallContext) -> ActionCallContext:
        """Called after each action execution completes."""
        return ctx

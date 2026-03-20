"""Base middleware class and shared context types.

A single Middleware type handles cross-cutting concerns at the turn,
model-call, and action levels through six lifecycle events:

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

ActionCall = Callable[[Action], Tuple[str, bool]]
ModelCall = Callable[[List[Dict[str, Any]]], str]


@dataclass
class TurnContext:
    """Shared state passed through the middleware chain for a single turn."""
    agent_name: str
    turn_num: int
    max_turns: int
    messages: List[Dict[str, str]]
    llm_response: Optional[str] = None
    result: Optional[ExecutionResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    aborted: bool = False
    abort_reason: Optional[str] = None


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

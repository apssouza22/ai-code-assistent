"""Stateless executor for single-turn agent execution with state management."""

import logging
from typing import Tuple, Dict, Callable, Optional, List

from src.core.action import (
    FinishAction, Action, SimpleActionParser
)
from src.core.common.middleware import Middleware, MiddlewarePipeline
from src.core.common.utils import format_tool_output
from src.core.action.actions_result import ExecutionResult
from src.misc import pretty_log

logger = logging.getLogger(__name__)


class ActionHandler:
    """Executes a single turn of agent interaction"""

    def __init__(
        self,
        actions: Dict[type, Callable],
        agent_name: str,
        middlewares: Optional[List[Middleware]] = None,
    ):
        self.agent_name = agent_name
        self._actions = actions
        self._pipeline = MiddlewarePipeline(middlewares)

    def handle_tools(self, tools: list[Action], env_responses) -> ExecutionResult:
        actions_executed = []
        finish_message = None
        done = False
        has_error = False

        for tool in tools:
            try:
                output, action_error = self._pipeline.execute_action(
                    tool, self._tool_call, self.agent_name
                )
                actions_executed.append(tool)
                env_responses.append(output)
                has_error = has_error or action_error
                if isinstance(tool, FinishAction):
                    finish_message = tool.message
                    done = True
                    pretty_log.success(f"Task finished: {tool.message}", self.agent_name.upper())
                    break

            except Exception as e:
                pretty_log.error(f"Action execution failed: {e}", self.agent_name.upper())
                env_responses.append(f"[ERROR] Action execution failed: {str(e)}")
                has_error = True

        return ExecutionResult(
            actions_executed=actions_executed,
            env_responses=env_responses,
            has_error=has_error,
            finish_message=finish_message,
            done=done,
            task_trajectories=None
        )

    def _tool_call(self, action: Action) -> Tuple[str, bool]:
        """Core handler lookup and dispatch — the innermost call in the middleware chain."""
        handler = self._actions.get(type(action))
        if handler:
            return handler(action)

        content = f"[ERROR] Unknown action type: {type(action).__name__}"
        return format_tool_output("unknown", content), True


    def get_tools(self, llm_output) -> Tuple[List[Action], List[str], bool]:
        actions, parsing_errors, found_action_attempt = SimpleActionParser.parse_llm_output(
            llm_output
        )

        if not found_action_attempt:
            pretty_log.warning("No actions attempted in response", self.agent_name.upper())
            return actions, ["No actions were attempted."], True

        env_responses = []
        has_error = False
        if parsing_errors:
            has_error = True
            for error in parsing_errors:
                pretty_log.debug(f"Parse error: {error}")
                env_responses.append(f"[PARSE ERROR] {error} \n USE BLOCK SCALARS (|) TO FIX MULTILINE STRINGS ISSUES!")

        pretty_log.info(f"Executing actions: {[type(a).__name__ for a in actions]}", self.agent_name.upper())
        return actions, env_responses, has_error

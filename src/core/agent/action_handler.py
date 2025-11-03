"""Stateless executor for single-turn agent execution with state management."""

import logging
from typing import Tuple, Dict, Callable

from src.core.action import (
    FinishAction, Action, SimpleActionParser
)
from src.core.common.utils import format_tool_output
from src.core.agent.actions_result import ExecutionResult
from src.misc import pretty_log

logger = logging.getLogger(__name__)


class ActionHandler:
    """Executes a single turn of agent interaction"""

    def __init__(self, actions: Dict[type, Callable], agent_name: str ):
        self.agent_name = agent_name
        self._actions = actions

    def execute(self, llm_output: str) -> ExecutionResult:
        """Execute actions from LLM output and return result.

        Args:
            llm_output: Raw output from the LLM

        Returns:
            ExecutionResult containing executed actions and responses
        """
        actions, env_responses, has_error = self._get_actions(llm_output)
        if not actions:
            return ExecutionResult(
                actions_executed=[],
                env_responses=env_responses,
                has_error=True,
                done=False
            )

        result = self._execute_actions(actions, env_responses)
        result.has_error = result.has_error or has_error
        return result

    def _execute_actions(self, actions: list[Action], env_responses) -> ExecutionResult:
        actions_executed = []
        finish_message = None
        done = False
        has_error = False
        for action in actions:
            try:
                pretty_log.debug(f"Executing action: {action}", agent_name=self.agent_name.upper())
                output, has_error = self._handle_action(action)
                actions_executed.append(action)
                env_responses.append(output)
                if isinstance(action, FinishAction):
                    finish_message = action.message
                    done = True
                    pretty_log.success(f"Task finished: {action.message}", self.agent_name.upper())
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

    def _handle_action(self, action: Action) -> Tuple[str, bool]:
        """Handle an action and return (response, is_error)."""
        handler = self._actions.get(type(action))
        if handler:
            return handler(action)

        content = f"[ERROR] Unknown action type: {type(action).__name__}"
        return format_tool_output("unknown", content), True


    def _get_actions(self, llm_output):
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
                pretty_log.error(f"Parse error: {error}")
                env_responses.append(f"[PARSE ERROR] {error} \n USE BLOCK SCALARS (|) TO FIX MULTILINE STRINGS ISSUES!")

        pretty_log.info(f"Executing actions: {[type(a).__name__ for a in actions]}", self.agent_name.upper())
        return actions, env_responses, has_error

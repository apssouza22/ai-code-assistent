import logging
from typing import Callable, Dict, List, Tuple

from src.core.action.actions import Action, FinishAction
from src.core.action.actions_result import ExecutionResult
from src.core.action.parser import SimpleActionParser
from src.core.common.utils import format_tool_output
from src.misc import pretty_log

logger = logging.getLogger(__name__)


class ActionHandler:
    def __init__(self, actions: Dict[type, Callable], agent_name: str):
        self._actions = actions
        self._agent_name = agent_name

    def get_tools(self, llm_output: str) -> Tuple[List[Action], List[str], bool]:
        actions, parsing_errors, found_action_attempt = SimpleActionParser.parse_llm_output(llm_output)

        env_responses: List[str] = []
        has_error = False

        if not found_action_attempt:
            pretty_log.warning("No actions were attempted.", self._agent_name)
            return actions, ["No actions were attempted."], True

        if parsing_errors:
            has_error = True
            for error in parsing_errors:
                env_responses.append(
                    f"[PARSE ERROR] {error} \n USE BLOCK SCALARS (|) TO FIX MULTILINE STRINGS ISSUES!"
                )

        action_names = [type(a).__name__ for a in actions]
        pretty_log.info(f"Executing actions: {action_names}", self._agent_name)

        return actions, env_responses, has_error

    def handle_tools(self, tools: List[Action], env_responses: List[str]) -> ExecutionResult:
        actions_executed: List[Action] = []
        finish_message = None
        done = False
        has_error = False

        for tool in tools:
            try:
                output, action_error = self.execute_tool_call(tool)
                actions_executed.append(tool)
                env_responses.append(output)
                has_error = has_error or action_error

                if isinstance(tool, FinishAction):
                    finish_message = tool.message
                    done = True
                    pretty_log.success(f"Task finished: {tool.message}", self._agent_name)
                    break
            except Exception as e:
                logger.error(f"Action execution failed: {e}")
                env_responses.append(f"[ERROR] Action execution failed: {str(e)}")
                has_error = True

        return ExecutionResult(
            actions_executed=actions_executed,
            env_responses=env_responses,
            has_error=has_error,
            finish_message=finish_message,
            done=done,
            task_trajectories=None,
        )

    def execute_tool_call(self, action: Action) -> Tuple[str, bool]:
        handler = self._actions.get(type(action))
        if handler:
            return handler(action)
        class_name = type(action).__name__
        return format_tool_output("unknown", f"[ERROR] Unknown action type: {class_name}"), True

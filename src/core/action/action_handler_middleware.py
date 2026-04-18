"""Parse LLM output into tools and execute them via the action pipeline."""

from typing import Optional, Dict, Callable

from src.core.action.actions import Action, BashAction, FinishAction
from src.core.action.actions_result import ExecutionResult
from src.core.action.action_handler import ActionHandler
from src.core.middleware.base import Middleware, ModelCallContext
from src.core.middleware.pipeline import MiddlewarePipeline
from src.misc import pretty_log


class ActionHandlerMiddleware(Middleware):
    """Parses ``ctx.response`` into actions and dispatches each through ``execute_action``.

    Runs in ``after_model_call`` so tool execution shares the same model-call lifecycle as tracing
    and logging around the LLM request.
    """

    def __init__(self, actions: Dict[type, Callable]) -> None:
        self._pipeline: Optional[MiddlewarePipeline] = None
        self._tool_handler = ActionHandler(actions=actions, agent_name="")

    def bind_pipeline(self, pipeline: MiddlewarePipeline) -> None:
        self._pipeline = pipeline

    def after_model_call(self, ctx: ModelCallContext) -> ModelCallContext:
        self._tool_handler._agent_name = ctx.agent_name
        pipeline = self._pipeline
        agent_name = ctx.agent_name
        if pipeline is None:
            raise ValueError("Pipeline not bound")

        if ctx.response is None:
            ctx.execution_result = ExecutionResult(
                actions_executed=[],
                actions_outputs=["[ERROR] Missing model response."],
                has_error=True,
                done=False,
            )
            return ctx

        actions, env_responses, parse_has_error = self._tool_handler.get_tools(ctx.response)
        if not actions:
            ctx.execution_result = ExecutionResult(
                actions_executed=[],
                actions_outputs=env_responses,
                has_error=True,
                done=False,
            )
            return ctx

        ctx.execution_result = self._execute_tools(actions, env_responses, pipeline, agent_name)
        ctx.execution_result.has_error = ctx.execution_result.has_error or parse_has_error
        return ctx

    def _execute_tools(
        self,
        tools: list[Action],
        exec_outputs: list[str],
        pipeline: MiddlewarePipeline,
        agent_name: str,
    ) -> ExecutionResult:
        actions_executed = []
        finish_message = None
        done = False
        has_error = False

        for tool in tools:
            try:
                if isinstance(tool, BashAction):
                    pretty_log.debug(f"Executing bash command: {tool.cmd}", agent_name.upper())

                output, action_error = pipeline.execute_action(
                    tool,
                    self._tool_handler.execute_tool_call,
                    agent_name,
                )
                actions_executed.append(tool)
                exec_outputs.append(output)
                has_error = has_error or action_error

                if isinstance(tool, FinishAction):
                    finish_message = tool.message
                    done = True
                    pretty_log.success(f"Task finished: {tool.message}", agent_name.upper())
                    break

            except Exception as e:
                pretty_log.error(f"Action execution failed: {e}", agent_name.upper())
                exec_outputs.append(f"[ERROR] Action execution failed: {str(e)}")
                has_error = True

        return ExecutionResult(
            actions_executed=actions_executed,
            actions_outputs=exec_outputs,
            has_error=has_error,
            finish_message=finish_message,
            done=done,
            task_trajectories=None,
        )

from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional, List

from src.core.action import Action, FinishAction
from src.core.action.action_handler import ActionHandler
from src.core.action.actions import BashAction
from src.core.action.actions_result import ExecutionResult
from src.core.agent.subagent_report import SubagentReport
from src.core.llm import get_llm_response
from src.core.llm.llm_config import LlmConfig
from src.core.middleware import MiddlewarePipeline, Middleware, TurnContext, AgentTaskContext
from src.misc import pretty_log


@dataclass
class AgentTask:
    """Base Task Agent class."""
    task_id: str
    instruction: str
    agent_name: str

AgentTaskReport = Dict[str, Any] | SubagentReport

class Agent:
    """Base Agent class."""

    def __init__(
        self,
        system_prompt: str,
        actions: Dict[type, Callable],
        agent_name: str,
        llm_config: LlmConfig,
        max_turns: int = 30,
        middlewares: List[Middleware] = None,
    ):
        self.agent_name = agent_name
        self.max_turns = max_turns
        self.llm_config = llm_config

        self.tool_handler = ActionHandler(
            actions=actions,
            agent_name=agent_name,
        )
        self.messages: List[Dict[str, str]] = []
        self.system_message = system_prompt
        self.pipeline = MiddlewarePipeline(middlewares)


    def run_task(self, task: AgentTask, max_turns: Optional[int] = None) -> AgentTaskReport:
        """Execute the task and return the report."""
        self.max_turns = max_turns or self.max_turns
        ctx = AgentTaskContext(
            task=task,
            agent_name=self.agent_name,
            system_message=self.system_message,
            messages=self.messages,
        )
        ctx = self.pipeline.execute_agent_task(ctx, self._handle_task)

        if ctx.aborted:
            return SubagentReport([], ctx.abort_reason or "Task aborted.")

        if ctx.task_exception:
            raise ctx.task_exception

        return ctx.task_result

    def _handle_task(self, agent_ctx: AgentTaskContext) -> AgentTaskContext:
        turn_ctx = TurnContext(
            agent_name=self.agent_name,
            turn_num=0,
            max_turns=self.max_turns,
            messages=self.messages,
            metadata={"task_title": agent_ctx.task.title},
            prompt=agent_ctx.task.instruction,
        )

        for turn_num in range(self.max_turns):
            turn_ctx.turn_num = turn_num
            turn_ctx =  self.pipeline.execute_turn(turn_ctx, self._turn)
            if turn_ctx.turn_exception:
                raise turn_ctx.turn_exception

            if turn_ctx.aborted:
                agent_ctx.aborted = True
                agent_ctx.abort_reason = turn_ctx.abort_reason
                return agent_ctx

            if turn_ctx.report:
                pretty_log.info(f"Subagent report comments: {turn_ctx.report.comments}", self.agent_name.upper())
                agent_ctx.task_result = turn_ctx.report
                return agent_ctx

        agent_ctx.task_result = SubagentReport([], "Reached max turns. Task not completed.")
        return agent_ctx

    def handle_turn(self, ctx: TurnContext) -> TurnContext:
        return self.pipeline.execute_turn(ctx, self._turn)

    def _turn(self, ctx: TurnContext) -> TurnContext:
        model_call_ctx = self.pipeline.execute_model_call(ctx.messages, self._get_llm_inference, self.agent_name)
        ctx.llm_response = model_call_ctx.response
        ctx.result = self.handle_llm_response(ctx.llm_response)
        return ctx

    def _get_llm_inference(self, messages: List[Dict[str, str]]) -> str:
        return get_llm_response(messages, self.llm_config)

    def handle_llm_response(self, llm_response: str) -> ExecutionResult:
        """Execute actions based on LLM response."""
        actions, env_responses, has_error = self.tool_handler.get_tools(llm_response)
        if not actions:
            return ExecutionResult(
                actions_executed=[],
                actions_outputs=env_responses,
                has_error=True,
                done=False
            )
        result = self._execute_tools(actions, env_responses)
        result.has_error = result.has_error or has_error
        return result

    def _execute_tools(self, tools: list[Action], exec_outputs) -> ExecutionResult:
        actions_executed = []
        finish_message = None
        done = False
        has_error = False

        for tool in tools:
            try:
                if isinstance(tool, BashAction):
                    pretty_log.debug(f"Executing bash command: {tool.cmd}", self.agent_name.upper())

                output, action_error = self.pipeline.execute_action(tool, self.tool_handler.execute_tool_call, self.agent_name)
                actions_executed.append(tool)
                exec_outputs.append(output)
                has_error = has_error or action_error

                if isinstance(tool, FinishAction):
                    finish_message = tool.message
                    done = True
                    pretty_log.success(f"Task finished: {tool.message}", self.agent_name.upper())
                    break

            except Exception as e:
                pretty_log.error(f"Action execution failed: {e}", self.agent_name.upper())
                exec_outputs.append(f"[ERROR] Action execution failed: {str(e)}")
                has_error = True

        return ExecutionResult(
            actions_executed=actions_executed,
            actions_outputs=exec_outputs,
            has_error=has_error,
            finish_message=finish_message,
            done=done,
            task_trajectories=None
        )

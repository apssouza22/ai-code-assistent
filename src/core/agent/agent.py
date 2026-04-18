from dataclasses import dataclass
from typing import Dict, Callable, Optional, List

from src.core.agent.agent_report import AgentReport
from src.core.llm import get_llm_response
from src.core.llm.llm_config import LlmConfig
from src.core.middleware import (
    MiddlewarePipeline,
    Middleware,
    TurnContext,
    AgentTaskContext,
    ActionHandlerMiddleware,
)


@dataclass
class AgentTask:
    """Base Task Agent class."""
    task_id: str
    instruction: str
    agent_name: str

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

        self.messages: List[Dict[str, str]] = []
        self.system_message = system_prompt
        action_handler_middleware = ActionHandlerMiddleware(actions)

        merged_middlewares = [*list(middlewares or []), action_handler_middleware]
        self.pipeline = MiddlewarePipeline(merged_middlewares)
        action_handler_middleware.bind_pipeline(self.pipeline)


    def run_task(self, task: AgentTask, max_turns: Optional[int] = None) -> AgentReport:
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
            return AgentReport(ctx.abort_reason or "Task aborted.")

        if ctx.task_exception:
            raise ctx.task_exception

        return ctx.task_result

    def _handle_task(self, agent_ctx: AgentTaskContext) -> AgentTaskContext:
        turn_ctx = TurnContext(
            agent_name=self.agent_name,
            turn_num=0,
            max_turns=self.max_turns,
            messages=self.messages,
            task=agent_ctx.task,
            prompt=agent_ctx.task.instruction,
        )

        for turn_num in range(self.max_turns):
            turn_ctx.turn_num = turn_num + 1
            turn_ctx =  self.pipeline.execute_turn(turn_ctx, self._turn)

            if turn_ctx.turn_exception:
                raise turn_ctx.turn_exception

            if turn_ctx.aborted:
                agent_ctx.aborted = True
                agent_ctx.abort_reason = turn_ctx.abort_reason
                return agent_ctx

            if turn_ctx.report:
                agent_ctx.task_result = turn_ctx.report
                return agent_ctx

        agent_ctx.task_result = AgentReport("Reached max turns. Task not completed.")
        return agent_ctx

    def handle_turn(self, ctx: TurnContext) -> TurnContext:
        return self.pipeline.execute_turn(ctx, self._turn)

    def _turn(self, turn_ctx: TurnContext) -> TurnContext:
        model_call_ctx = self.pipeline.execute_model_call(turn_ctx.messages, self._get_llm_inference, self.agent_name)
        turn_ctx.llm_response = model_call_ctx.response
        turn_ctx.result = model_call_ctx.execution_result
        return turn_ctx

    def _get_llm_inference(self, messages: List[Dict[str, str]]) -> str:
        return get_llm_response(messages, self.llm_config)

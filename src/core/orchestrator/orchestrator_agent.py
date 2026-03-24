"""TechLead Orchestrator Agent using stateless execution pattern."""

from typing import Any, Dict, Optional, Callable

from src.core.agent import Agent, AgentTask
from src.core.context import ContextStore
from src.core.llm import LlmConfig, get_llm_response
from src.core.orchestrator.session_history import SessionHistory
from src.core.orchestrator.turn import Turn, TurnContext
from src.core.orchestrator.turn_history import TurnHistory
from src.core.task import TaskManager, TaskStore
from src.misc import pretty_log


class OrchestratorAgent(Agent):
    """Orchestrator agent coordinating tasks and subagents."""

    def __init__(
        self,
        system_prompt: str,
        task_store: TaskStore,
        context_store: ContextStore,
        task_manager: TaskManager,
        actions: Dict[type, Callable],
        llm_config: LlmConfig,
    ):
        super().__init__(
            system_prompt=system_prompt,
            actions=actions,
            agent_name="orchestrator",
            llm_config=llm_config,
        )
        pretty_log.info(f"OrchestratorAgent initialized with model={llm_config.model}, temperature={llm_config.temperature}")
        self.task_manager = task_manager
        self.task_store = task_store
        self.context_store = context_store
        self.turn_history = TurnHistory()
        self.session_history = SessionHistory(
            task_store=task_store,
            context_store=context_store,
            turn_history=self.turn_history
        )

    def _run_turn(self, ctx: TurnContext) -> TurnContext:
        """Core turn logic: LLM call, action execution, state update.

        This is the innermost function wrapped by the middleware pipeline.
        """
        agent_prompt = f"## Current Task\n{ctx.user_message}\n\n{self.session_history.to_prompt()}"
        llm_response = self._get_llm_response(agent_prompt)
        result = self.handle_llm_response(llm_response)
        turn = Turn(
            llm_output=llm_response,
            actions_executed=result.actions_executed,
            action_outputs=result.actions_outputs,
            task_trajectories=result.task_trajectories
        )
        self.turn_history.add_turn(turn)
        self.session_history.done = result.done
        self.session_history.finish_message = result.finish_message
        ctx.turn = turn
        ctx.result = result
        return ctx

    def _handle_turn(self, instruction: str, turn_num: int, max_turns: int) -> TurnContext:
        ctx = TurnContext(
            agent_name=self.agent_name,
            turn_num=turn_num,
            max_turns=max_turns,
            messages=self.messages,
            user_message=instruction,
        )
        self._run_turn(ctx)
        return ctx


    def _get_llm_response(self, agent_prompt: str) -> str:
        call_messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": agent_prompt},
        ]
        response = get_llm_response(messages=call_messages, llm_config=self.llm_config)
        self.messages.append({"role": "user", "content": agent_prompt})
        self.messages.append({"role": "assistant", "content": response})
        return response

    def run_task(self, task: AgentTask, max_turns: Optional[int] = None) -> Dict[str, Any]:
        turns_executed = 0
        pretty_log.section_header(f"Starting Task: {task.instruction}")
        while not self.session_history.done and turns_executed < max_turns:
            turns_executed += 1
            ctx = self._handle_turn(task.instruction, turns_executed, max_turns)
            pretty_log.debug(f"Action output: {ctx.result.actions_outputs}", "ORCHESTRATOR")
            if ctx.aborted:
                pretty_log.warning(f"Turn aborted: {ctx.abort_reason}", "ORCHESTRATOR")
                break
            if ctx.result.done:
                pretty_log.success(f"Task completed: {ctx.result.finish_message}", "ORCHESTRATOR")
                break

        return {
            'completed': self.session_history.done,
            'finish_message': self.session_history.finish_message,
            'turns_executed': turns_executed,
            'max_turns_reached': turns_executed >= max_turns
        }

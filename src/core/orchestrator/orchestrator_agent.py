"""TechLead Orchestrator Agent using stateless execution pattern."""

from typing import Any, Dict, Optional, Callable

from src.core.agent import Agent, AgentTask
from src.core.context import ContextStore
from src.core.llm import LlmConfig
from src.core.middleware import TurnContext
from src.core.orchestrator.session_history import SessionHistory
from src.core.orchestrator.turn import Turn
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

    def _handle_turn(self, instruction: str, turn_num: int, max_turns: int) -> TurnContext:
        ctx = TurnContext(
            agent_name=self.agent_name,
            turn_num=turn_num,
            max_turns=max_turns,
            messages=self.messages,
            prompt=instruction,
        )
        agent_prompt = f"## Current Task\n{ctx.prompt}\n\n{self.session_history.to_prompt()}"

        self.messages.append({"role": "system", "content": self.system_message})
        self.messages.append({"role": "user", "content": agent_prompt})

        ctx = self.handle_turn(ctx)
        result = ctx.result

        turn = Turn(
            llm_output=ctx.llm_response,
            actions_executed=result.actions_executed,
            action_outputs=result.actions_outputs,
            task_trajectories=result.task_trajectories
        )
        self.turn_history.add_turn(turn)
        self.session_history.done = result.done
        self.session_history.finish_message = result.finish_message
        ctx.result = result
        return ctx

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

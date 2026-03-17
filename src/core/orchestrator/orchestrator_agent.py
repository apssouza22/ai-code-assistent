"""TechLead Orchestrator Agent using stateless execution pattern."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from src.core.middleware import Middleware, TurnContext
from src.core.agent import Agent, AgentTask
from src.core.context import ContextStore
from src.core.llm import get_llm_response, LlmConfig
from src.core.orchestrator.session_history import SessionHistory
from src.core.orchestrator.turn import Turn
from src.core.orchestrator.turn_history import TurnHistory
from src.core.task import TaskManager, TaskStore
from src.misc import setup_file_logging, pretty_log

logger = logging.getLogger(__name__)
setup_file_logging("ERROR")


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
      logging_dir: Optional[Path] = None,
      middlewares: Optional[List[Middleware]] = None,
  ):
    super().__init__(
        system_prompt=system_prompt,
        actions=actions,
        agent_name="orchestrator",
        llm_config=llm_config,
        logging_dir=logging_dir,
        middlewares=middlewares,
    )
    logger.info(f"OrchestratorAgent initialized with model={llm_config.model}, temperature={llm_config.temperature}")
    self.task_manager = task_manager
    self.task_store = task_store
    self.context_store = context_store
    self.turn_history = TurnHistory()
    self.session_history = SessionHistory(
        task_store=task_store,
        context_store=context_store,
        turn_history=self.turn_history
    )

  def _core_turn(self, ctx: TurnContext) -> TurnContext:
    """Core turn logic: LLM call, action execution, state update.

    This is the innermost function wrapped by the middleware pipeline.
    """
    user_message = f"## Current Task\n{ctx.metadata['instruction']}\n\n{self.session_history.to_prompt()}"

    llm_response = self._get_llm_response(user_message)
    ctx.llm_response = llm_response

    result = self.handle_llm_response(llm_response)
    result.task_trajectories = self.task_manager.get_and_clear_task_trajectories()
    ctx.result = result

    turn = Turn(
        llm_output=llm_response,
        actions_executed=result.actions_executed,
        env_responses=result.env_responses,
        task_trajectories=result.task_trajectories
    )
    self.turn_history.add_turn(turn)
    self.session_history.done = result.done
    self.session_history.finish_message = result.finish_message
    ctx.metadata["turn"] = turn
    ctx.metadata["user_message"] = user_message

    self._log_turn_file(ctx)

    return ctx

  def _handle_turn(self, instruction: str, turn_num: int, max_turns: int) -> Dict[str, Any]:
    ctx = TurnContext(
        agent_name=self.agent_name,
        turn_num=turn_num,
        max_turns=max_turns,
        messages=self.messages,
        metadata={"instruction": instruction},
    )

    ctx = self.pipeline.execute_turn(ctx, self._core_turn)

    if ctx.aborted:
      return {
        'done': False,
        'finish_message': None,
        'has_error': True,
        'actions_executed': 0,
        'turn': None,
        'aborted': True,
        'abort_reason': ctx.abort_reason,
      }

    result = ctx.result
    return {
      'done': result.done,
      'finish_message': result.finish_message,
      'has_error': result.has_error,
      'actions_executed': len(result.actions_executed),
      'turn': ctx.metadata.get("turn"),
    }

  def _log_turn_file(self, ctx: TurnContext):
    """Write structured turn data to the file logger (if enabled)."""
    if not self.turn_logger:
      return

    result = ctx.result
    turn_data = {
      "instruction": ctx.metadata.get("instruction"),
      "user_message": ctx.metadata.get("user_message"),
      "llm_response": ctx.llm_response,
      "actions_executed": [str(a) for a in result.actions_executed],
      "env_responses": result.env_responses,
      "task_trajectories": result.task_trajectories,
      "done": result.done,
      "finish_message": result.finish_message,
      "has_error": result.has_error,
      "state_snapshot": self.session_history.to_dict(),
      **{k: v for k, v in ctx.metadata.items()
         if k not in ("instruction", "user_message", "turn")},
    }
    self.turn_logger.log_turn(ctx.turn_num, turn_data)

  def _get_llm_response(self, user_message: str) -> str:
    response = get_llm_response(
        messages=[
          {"role": "system", "content": self.system_message},
          {"role": "user", "content": user_message}
        ],
        llm_config=self.llm_config,
        api_base=self.api_base
    )

    self.messages.append({"role": "user", "content": user_message})
    self.messages.append({"role": "assistant", "content": response})
    return response

  def run_task(self, task: AgentTask, max_turns: Optional[int] = None) -> Dict[str, Any]:
    turns_executed = 0
    pretty_log.section_header(f"Starting Task: {task.instruction}")
    while not self.session_history.done and turns_executed < max_turns:
      turns_executed += 1
      result = self._handle_turn(task.instruction, turns_executed, max_turns)

      if result.get('aborted'):
        pretty_log.warning(f"Turn aborted: {result.get('abort_reason')}", "ORCHESTRATOR")
        break

      if result['done']:
        pretty_log.success(f"Task completed: {result['finish_message']}", "ORCHESTRATOR")
        break

    return {
      'completed': self.session_history.done,
      'finish_message': self.session_history.finish_message,
      'turns_executed': turns_executed,
      'max_turns_reached': turns_executed >= max_turns
    }

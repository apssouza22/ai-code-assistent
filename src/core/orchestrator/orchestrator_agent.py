"""TechLead Orchestrator Agent using stateless execution pattern."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Callable

from src.core.agent import ExecutionResult, Agent, AgentTask
from src.core.context import ContextStore
from src.core.llm import get_llm_response
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
      model: Optional[str] = None,
      temperature: Optional[float] = None,
      api_key: Optional[str] = None,
      logging_dir: Optional[Path] = None,
  ):
    super().__init__(
        system_prompt=system_prompt,
        actions=actions,
        agent_name="orchestrator",
        model=model,
        temperature=temperature,
        api_key=api_key,
        api_base=None,
        logging_dir=logging_dir,
    )
    logger.info(f"OrchestratorAgent initialized with model={model}, temperature={temperature}")
    self.task_manager = task_manager
    self.task_store = task_store
    self.context_store = context_store
    self.turn_history = TurnHistory()
    self.session_history = SessionHistory(
        task_store=task_store,
        context_store=context_store,
        turn_history=self.turn_history
    )

  def _handle_turn(self, instruction: str, turn_num: int, max_turns: int) -> Dict[str, Any]:
    pretty_log.info(f"Turn {turn_num}/{max_turns} starting", "ORCHESTRATOR")
    user_message = f"## Current Task\n{instruction}\n\n{self.session_history.to_prompt()}"

    llm_response = self._get_llm_response(user_message)
    result = self.handle_llm_response(llm_response)
    result.task_trajectories = self.task_manager.get_and_clear_task_trajectories()

    turn = Turn(
        llm_output=llm_response,
        actions_executed=result.actions_executed,
        env_responses=result.env_responses,
        task_trajectories=result.task_trajectories
    )
    self.turn_history.add_turn(turn)
    self.session_history.done = result.done
    self.session_history.finish_message = result.finish_message
    self._log_turn(instruction, llm_response, result, turn_num, user_message)

    return {
      'done': result.done,
      'finish_message': result.finish_message,
      'has_error': result.has_error,
      'actions_executed': len(result.actions_executed),
      'turn': turn
    }

  def _log_turn(self, instruction: str, llm_response: str, result: ExecutionResult, turn_num: int, user_message: str):
    pretty_log.debug(f"Actions executed - Count: {len(result.actions_executed)}", "ORCHESTRATOR")

    if result.task_trajectories:
      pretty_log.debug(f"Received {len(result.task_trajectories)} subagent report(s)", "ORCHESTRATOR")
      for task_id, trajectory in result.task_trajectories.items():
        pretty_log.info(f"Subagent performed Task {task_id}: {trajectory.get('title', 'Unknown')}", "ORCHESTRATOR")
    else:
      pretty_log.debug("No subagent reports in this turn", "ORCHESTRATOR")

    if self.turn_logger:
      turn_data = {
        "instruction": instruction,
        "user_message": user_message,
        "llm_response": llm_response,
        "actions_executed": [str(action) for action in result.actions_executed],
        "env_responses": result.env_responses,
        "task_trajectories": result.task_trajectories,
        "done": result.done,
        "finish_message": result.finish_message,
        "has_error": result.has_error,
        "state_snapshot": self.session_history.to_dict()
      }
      self.turn_logger.log_turn(turn_num, turn_data)

    if result.done:
      pretty_log.success(f"Task marked as DONE - {result.finish_message}", "ORCHESTRATOR")
    else:
      pretty_log.debug(f"Turn {turn_num} complete - Continuing...\n", "ORCHESTRATOR")

  def _get_llm_response(self, user_message: str) -> str:
    response = get_llm_response(
        messages=[
          {"role": "system", "content": self.system_message},
          {"role": "user", "content": user_message}
        ],
        model=self.model,
        temperature=self.temperature,
        max_tokens=4096,
        api_key=self.api_key,
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
      try:
        result = self._handle_turn(task.instruction, turns_executed, max_turns)
        if result['done']:
          pretty_log.success(f"Task completed: {result['finish_message']}", "ORCHESTRATOR")
          break

      except Exception as e:
        logger.error(f"Error in turn {turns_executed}: {e}")
        pretty_log.error(f"Error in turn {turns_executed}: {e}", "ORCHESTRATOR")
        import traceback
        traceback.print_exc()

    return {
      'completed': self.session_history.done,
      'finish_message': self.session_history.finish_message,
      'turns_executed': turns_executed,
      'max_turns_reached': turns_executed >= max_turns
    }

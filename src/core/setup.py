import json
import logging
import os
from pathlib import Path
from typing import Optional, List, Tuple

from terminal_bench import BaseAgent
from terminal_bench.agents.base_agent import AgentResult
from terminal_bench.harness_models import FailureMode
from terminal_bench.terminal.tmux_session import TmuxSession

from src.core.agent import AgentTask
from src.core.llm import count_input_tokens, count_output_tokens
from src.core.orchestrator.factory import create_orchestrator_agent
from src.core.bash import DockerExecutor

logger = logging.getLogger(__name__)

class AgentSetup(BaseAgent):

    def __init__(self,
        system_message_path: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        **kwargs  # Accept additional keyword arguments from terminal bench
    ):
        super().__init__(**kwargs)
        self.orchestrator = None
        self.turn_logger = None
        self.api_base = api_base
        self.api_key = api_key
        self.temperature = temperature
        self.model = model
        self.system_message_path = system_message_path

    @staticmethod
    def name() -> str:
        return "OrchestratorAgent"


    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        container_name = session.container.name
        if not container_name:
            raise ValueError("Container name is required for DockerExecutor")

        timestamped_markers: List[Tuple[float, str]] = []
        log_file = self._log_info(logging_dir)
        total_input_tokens = 0
        total_output_tokens = 0

        docker_executor = DockerExecutor(container_name=container_name)
        self.orchestrator = create_orchestrator_agent(
            model=self.model,
            temperature=self.temperature,
            container_name=container_name,
            command_executor=docker_executor,
            api_key=os.getenv("LITE_LLM_API_KEY") or os.getenv("LITELLM_API_KEY"),
            logging_dir=logging_dir,
        )

        try:
            agent_task = AgentTask(
                task_id="orchestrator_task_1",
                instruction=instruction,
                agent_name="orchestrator",
            )
            result = self.orchestrator.run_task(agent_task, max_turns=50)
            subagent_input_tokens = 0
            subagent_output_tokens = 0

            # Iterate through conversation history to find all subagent trajectories
            if self.orchestrator.turn_history and self.orchestrator.turn_history.turns:
                for turn in self.orchestrator.turn_history.turns:
                    if turn.subagent_trajectories:
                        for task_id, trajectory_data in turn.subagent_trajectories.items():
                            subagent_input_tokens += trajectory_data.get('total_input_tokens', 0)
                            subagent_output_tokens += trajectory_data.get('total_output_tokens', 0)
                            logger.info(f"Subagent {task_id} tokens - Input: {trajectory_data.get('total_input_tokens', 0)}, Output: {trajectory_data.get('total_output_tokens', 0)}")

            orchestrator_input_tokens = count_input_tokens(self.orchestrator.messages, self.model)
            orchestrator_output_tokens = count_output_tokens(self.orchestrator.messages, self.model)
            total_input_tokens = subagent_input_tokens + orchestrator_input_tokens
            total_output_tokens = subagent_output_tokens + orchestrator_output_tokens
            failure_mode = self._get_failure_mode(result)

            logger.info(f"Orchestrator tokens - Input: {orchestrator_input_tokens}, Output: {orchestrator_output_tokens}")
            logger.info(f"Total tokens (orchestrator + subagents) - Input: {total_input_tokens}, Output: {total_output_tokens}")

        except Exception as e:
            logger.exception(f"Error during orchestrator execution: {e}")
            failure_mode = FailureMode.UNKNOWN_AGENT_ERROR

        # Save conversation log if logging directory provided
        if log_file:
            data = {
                "instruction": instruction,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "failure_mode": failure_mode.value,
                "timestamped_markers": timestamped_markers,
                "final_state": self.orchestrator.session_history.to_dict() if self.orchestrator.session_history else "",
            }

            # Get path and save the log
            path = log_file.resolve().parent
            with open(path / 'conversation_log.json', 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Conversation log exported to: {path / 'conversation_log.json'}")

        return AgentResult(
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            failure_mode=failure_mode,
            timestamped_markers=timestamped_markers,
        )

    @staticmethod
    def _get_failure_mode(result):
        failure_mode = FailureMode.NONE
        if result['completed']:
            failure_mode = FailureMode.NONE
        elif result['max_turns_reached']:
            failure_mode = FailureMode.AGENT_TIMEOUT
        else:
            failure_mode = FailureMode.UNKNOWN_AGENT_ERROR
        return failure_mode

    @staticmethod
    def _log_info(logging_dir):
        if logging_dir:
            logging_dir = Path(logging_dir)
            logging_dir.mkdir(exist_ok=True, parents=True)
        return logging_dir

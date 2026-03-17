from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Callable, Optional, List

from src.core.middleware import Middleware, MiddlewarePipeline
from src.core.agent.action_handler import ActionHandler
from src.core.agent.actions_result import ExecutionResult
from src.core.llm import count_input_tokens, count_output_tokens
from src.core.llm.llm_config import LlmConfig
from src.misc import TurnLogger


@dataclass
class AgentTask:
    """Base Task Agent class."""
    task_id: str
    instruction: str
    agent_name: str

@dataclass
class TaskAgentResult:
    """Result of a Task Agent execution."""
    output: str
    meta: Dict[str, Any]

class Agent:
    """Base Agent class."""

    def __init__(self,
        system_prompt: str,
        actions: Dict[type, Callable],
        agent_name: str,
        llm_config: LlmConfig,
        max_turns: int = 30,
        api_base: Optional[str] = None,
        logging_dir: Optional[Path] = None,
        middlewares: Optional[List[Middleware]] = None,
    ):
        self.agent_name = agent_name
        self.max_turns = max_turns
        self.llm_config = llm_config
        self.api_base = api_base
        self.tool_handler = ActionHandler(
            actions=actions,
            agent_name=agent_name,
            middlewares=middlewares,
        )
        self.messages: List[Dict[str, str]] = []
        self.system_message = system_prompt
        self.turn_logger = TurnLogger(logging_dir, agent_name) if logging_dir else None
        self.pipeline = MiddlewarePipeline(middlewares)

        self.messages = []


    @property
    def total_input_tokens(self) -> int:
        """Calculate total input tokens from all messages."""
        return count_input_tokens(self.messages, self.llm_config.model)

    @property
    def total_output_tokens(self) -> int:
        """Calculate total output tokens from all messages."""
        return count_output_tokens(self.messages, self.llm_config.model)

    @abstractmethod
    def run_task(self, task: AgentTask, max_turns: Optional[int] = None) -> Dict[str, Any]:
        pass


    def handle_llm_response(self, llm_response: str) -> ExecutionResult:
        """Execute actions based on LLM response."""
        actions, env_responses, has_error = self.tool_handler.get_tools(llm_response)
        if not actions:
            return ExecutionResult(
                actions_executed=[],
                env_responses=env_responses,
                has_error=True,
                done=False
            )
        result = self.tool_handler.handle_tools(actions, env_responses)
        result.has_error = result.has_error or has_error
        return result

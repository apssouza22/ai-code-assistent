"""Subagent implementation for executing delegated tasks."""

from typing import Callable, Dict, List

from src.core.agent.agent import Agent
from src.core.llm.llm_config import LlmConfig
from src.core.middleware import Middleware


class Subagent(Agent):
    """Executes a specific task delegated by the orchestrator."""

    def __init__(
        self,
        agent_name: str,
        system_prompt: str,
        actions: Dict[type, Callable],
        llm_config: LlmConfig,
        max_turns: int = 30,
        middlewares: List[Middleware] = None,
    ):
        super().__init__(
            agent_name=agent_name,
            system_prompt=system_prompt,
            actions=actions,
            llm_config=llm_config,
            max_turns=max_turns,
            middlewares=middlewares
        )


"""Subagent implementation for executing delegated tasks."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Callable

from src.core.agent.agent import AgentTask, Agent
from src.core.agent.subagent_report import SubagentReport
from src.core.llm import get_llm_response
from src.core.llm.llm_config import LlmConfig
from src.misc import pretty_log


@dataclass
class SubagentTask(AgentTask):
    """Task specification for a subagent."""
    agent_name: str
    title: str
    description: Optional[str]
    task_context: Dict[str, str]
    relevant_files: List[Dict[str, str]]


class Subagent(Agent):
    """Executes a specific task delegated by the orchestrator."""

    def __init__(
        self,
        agent_name: str,
        system_prompt: str,
        actions: Dict[type, Callable],
        llm_config: LlmConfig,
        max_turns: int = 30,
    ):
        super().__init__(
            system_prompt=system_prompt,
            actions=actions,
            max_turns=max_turns,
            llm_config=llm_config,
            agent_name=agent_name,
        )


    @staticmethod
    def _build_task_prompt(task: SubagentTask) -> str:
        """Build the initial task prompt with all context."""
        sections = [f"# Task: {task.title}\n", f"{task.description}\n"]
        if task.task_context:
            sections.append("## Provided Context\n")
            for ctx_id, content in task.task_context.items():
                sections.append(f"### Context: {ctx_id}\n")
                sections.append(f"{content}\n")

        if task.relevant_files:
            sections.append("## Relevant Files/Directories\n")
            for item in task.relevant_files:
                sections.append(f"- {item['path']}: {item['reason']}\n")

        sections.append("\nBegin your investigation/implementation now.")

        return "\n".join(sections)

    def run_task(self, task: SubagentTask, max_turns: int = None) -> SubagentReport:
        """Execute the task and return the report."""
        self.max_turns = max_turns or self.max_turns
        self.messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": self._build_task_prompt(task)}
        ]
        llm_response = get_llm_response(messages=self.messages, llm_config=self.llm_config)

        result = self.handle_llm_response(llm_response)
        str_result = "\n".join(result.actions_outputs)
        pretty_log.info(f"Subagent result: {str_result}", self.agent_name)
        # TODO: implement the action execution loop here

        return SubagentReport([], str_result)


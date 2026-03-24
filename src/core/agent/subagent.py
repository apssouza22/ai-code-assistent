"""Subagent implementation for executing delegated tasks."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Callable

from src.core.action import ReportAction
from src.core.agent.agent import AgentTask, Agent, TurnContext
from src.core.agent.subagent_report import SubagentReport, ContextItem
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

        for turn_num in range(self.max_turns):
            report = self._handle_turn(task, turn_num)
            if report:
                pretty_log.info(f"Subagent report comments: {report.comments}", self.agent_name.upper())
                return report

        return SubagentReport([], "Reached max turns. Task not completed.")

    def _handle_turn(self, task, turn_num)-> Optional[SubagentReport]:
        ctx = TurnContext(
            agent_name=self.agent_name,
            turn_num=turn_num + 1,
            max_turns=self.max_turns,
            messages=self.messages,
            metadata={"task_title": task.title},
            prompt=task.instruction,
        )

        ctx.llm_response = get_llm_response(self.messages, self.llm_config)
        ctx.result = self.handle_llm_response(ctx.llm_response)
        outputs = "\n".join(ctx.result.actions_outputs)
        ctx.metadata["_report"] = self._check_for_report(ctx.result.actions_executed)

        pretty_log.debug(f"Action output: {outputs}", self.agent_name.upper())
        self.messages.append({"role": "assistant", "content": ctx.llm_response})
        self.messages.append({"role": "user", "content": outputs})

        if ctx.aborted:
            self.messages.append({
                "role": "user",
                "content": f"Turn aborted: {ctx.abort_reason}. Please continue.",
            })
            return None

        if ctx.metadata.get("turn_error"):
            self.messages.append({
                "role": "user",
                "content": f"Error occurred: {ctx.metadata['turn_error']}. Please continue.",
            })
            return None

        return ctx.metadata.get("_report")

    @staticmethod
    def _check_for_report(actions: List) -> Optional[SubagentReport]:
        """Check if any action is a ReportAction and convert to SubagentReport."""

        for action in actions:
            if isinstance(action, ReportAction):
                contexts = [ContextItem(id=ctx["id"], content=ctx["content"]) for ctx in action.contexts]
                return SubagentReport(
                    contexts=contexts,
                    comments=action.comments,
                )
        return None

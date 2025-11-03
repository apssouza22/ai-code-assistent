"""Subagent implementation for executing delegated tasks."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Callable

from src.core.action import ReportAction
from src.core.agent.agent import AgentTask, Agent
from src.core.agent.subagent_report import ContextItem, SubagentMeta, SubagentReport
from src.core.llm import get_llm_response
from src.misc import pretty_log

logger = logging.getLogger(__name__)


@dataclass
class SubagentTask(AgentTask):
    """Task specification for a subagent."""
    agent_name: str
    title: str
    description: str
    task_id: str
    task_context: Dict[str, str]  # Resolved context content from store
    bootstrap_ctx: List[Dict[str, str]]  # List of {"path": str, "content": str, "reason": str}


class Subagent(Agent):
    """Executes a specific task delegated by the orchestrator."""

    def __init__(
        self,
        agent_name: str,
        system_prompt: str,
        actions: Dict[type, Callable],
        max_turns: int = 30,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        logging_dir: Optional[Path] = None
    ):
        self.report: Optional[SubagentReport] = None
        super().__init__(
            system_prompt=system_prompt,
            actions=actions,
            max_turns=max_turns,
            model=model,
            temperature=temperature,
            api_key=api_key,
            api_base=api_base,
            logging_dir=logging_dir,
            agent_name=agent_name
        )


    @staticmethod
    def _build_task_prompt(task: SubagentTask) -> str:
        """Build the initial task prompt with all context."""
        sections = [f"# Task: {task.title}\n", f"{task.description}\n"]
        # Include resolved contexts
        if task.task_context:
            sections.append("## Provided Context\n")
            for ctx_id, content in task.task_context.items():
                sections.append(f"### Context: {ctx_id}\n")
                sections.append(f"{content}\n")

        # Include bootstrap files/dirs
        if task.bootstrap_ctx:
            sections.append("## Relevant Files/Directories\n")
            for item in task.bootstrap_ctx:
                sections.append(f"- {item['path']}: {item['reason']}\n")

        sections.append("\nBegin your investigation/implementation now.")

        return "\n".join(sections)

    def _get_llm_response(self, messages: List[Dict[str, str]]) -> str:
        """Get response from LLM using centralized client."""
        return get_llm_response(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=4096,
            api_key=self.api_key,
            api_base=self.api_base
        )

    def _check_for_report(self, actions: List) -> Optional[SubagentReport]:
        """Check if any action is a ReportAction and convert to SubagentReport."""
        for action in actions:
            if isinstance(action, ReportAction):
                contexts = [
                    ContextItem(id=ctx["id"], content=ctx["content"]) for ctx in action.contexts
                ]
                return SubagentReport(
                    contexts=contexts,
                    comments=action.comments,
                    meta=SubagentMeta(
                        trajectory=self.messages.copy() if hasattr(self, 'messages') else None,
                        total_input_tokens=0,  # Will be set in run()
                        total_output_tokens=0  # Will be set in run()
                    )
                )
        return None

    def run_task(self, task: SubagentTask, max_turns: int = None) -> SubagentReport:
        """Execute the task and return the report."""
        self.max_turns = max_turns or self.max_turns
        if self.turn_logger:
            self.turn_logger.prefix = self.agent_name + f"_{task.task_id}"

        self.messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": self._build_task_prompt(task)}
        ]

        for turn_num in range(self.max_turns):
            pretty_log.debug(f"Executing turn {turn_num + 1}", self.agent_name.upper())
            try:
                report = self._handle_turn(task, turn_num)
                if report:
                    self._handle_report(report, task, turn_num)
                    return report
            except Exception as e:
                pretty_log.error(f"Error in turn {turn_num + 1}: {e}", self.agent_name.upper())
                self.messages.append({"role": "user", "content": f"Error occurred: {str(e)}. Please continue."})

        self._handle_max_turns_exceeded(task)


    def _handle_turn(self, task, turn_num):
        llm_response = self._get_llm_response(self.messages)
        self.messages.append({"role": "assistant", "content": llm_response})
        result = self.handle_llm_response(llm_response)
        env_response = "\n".join(result.env_responses)
        self.messages.append({"role": "user", "content": env_response})
        report = self._check_for_report(result.actions_executed)

        pretty_log.debug(f"Environment response received: {env_response[:200]}", self.agent_name.upper())
        if self.turn_logger:
            turn_data = {
                "task_type": self.agent_name,
                "task_title": task.title,
                "llm_response": llm_response,
                "actions_executed": [str(action) for action in result.actions_executed],
                "env_responses": result.env_responses,
                "messages_count": len(self.messages)
            }
            self.turn_logger.log_turn(turn_num + 1, turn_data)
        return report

    def _handle_report(self, report, task, turn_num):
        self.report = report
        report.meta.num_turns = turn_num + 1
        report.meta.total_input_tokens = self.total_input_tokens
        report.meta.total_output_tokens = self.total_output_tokens

        pretty_log.debug(f"Contexts returned: {len(report.contexts)} after {turn_num + 1} turns", self.agent_name.upper())
        pretty_log.debug(f"Total tokens - Input: {report.meta.total_input_tokens} Output: {report.meta.total_output_tokens}", self.agent_name.upper())

    def _handle_max_turns_exceeded(self, task):
        pretty_log.warning("Reached max turns without reporting - forcing report", self.agent_name.upper())
        if self.turn_logger:
            turn_data = {
                "task_type": self.agent_name,
                "task_title": task.title,
                "event": "forcing_report",
                "reason": "max_turns_reached"
            }
            self.turn_logger.log_turn(self.max_turns + 1, turn_data)

        # Append the force report message to the last user message (env_response)
        if self.messages and self.messages[-1]["role"] == "user":
            self.messages[-1]["content"] += force_report_msg
        else:
            # Fallback: add as new message if last message isn't user
            self.messages.append({"role": "user", "content": force_report_msg.strip()})

        try:
            llm_response = self._get_llm_response(self.messages)
            self.messages.append({"role": "assistant", "content": llm_response})
            result = self.action_handler.execute(llm_response)
            report = self._check_for_report(result.actions_executed)

            if report:
                self._handle_report(report, task, self.max_turns)
                if self.turn_logger:
                    summary_data = {
                        "task_type": self.agent_name,
                        "task_title": task.title,
                        "completed": True,
                        "num_turns": report.meta.num_turns,
                        "total_input_tokens": report.meta.total_input_tokens,
                        "total_output_tokens": report.meta.total_output_tokens,
                        "contexts_returned": len(report.contexts),
                        "comments": report.comments
                    }
                    self.turn_logger.log_final_summary(summary_data)
                return report

        except Exception as e:
            pretty_log.error(f"Error forcing report: {e}", self.agent_name.upper())

        return self._fallback_agent_report(task)

    def _fallback_agent_report(self, task):
        # Fallback if agent still doesn't provide report
        pretty_log.warning(f"FALLBACK - No report provided after {self.max_turns} turns", self.agent_name.upper())
        pretty_log.warning(f"Creating fallback report for task: {task.title}", self.agent_name.upper())

        return SubagentReport(
            contexts=[],
            comments=f"Task incomplete - reached maximum turns ({self.max_turns}) without proper completion. Agent failed to provide report when requested.",
            meta=SubagentMeta(
                trajectory=self.messages.copy(),
                num_turns=self.max_turns,
                total_input_tokens=self.total_input_tokens,
                total_output_tokens=self.total_output_tokens
            )
        )


# Create a forceful message requiring only a report action
force_report_msg = (
    "\n\n⚠️ CRITICAL: MAXIMUM TURNS REACHED ⚠️\n"
    "You have reached the maximum number of allowed turns.\n"
    "You MUST now submit a report using ONLY the <report> action.\n"
    "NO OTHER ACTIONS ARE ALLOWED.\n\n"
    "Instructions:\n"
    "1. Use ONLY the <report> action\n"
    "2. Include ALL contexts you have discovered so far\n"
    "3. In the comments section:\n"
    "   - Summarize what you have accomplished\n"
    "   - If the task is incomplete, explain what remains to be done\n"
    "   - Describe what you were about to do next and why\n\n"
    "SUBMIT YOUR REPORT NOW."
)

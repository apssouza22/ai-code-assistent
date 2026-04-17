"""Subagent task type and prompt construction."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.core.agent.agent import AgentTask


@dataclass
class SubagentTask(AgentTask):
    """Task specification for a subagent."""
    agent_name: str
    title: str
    description: Optional[str]
    task_context: Dict[str, str]
    relevant_files: List[Dict[str, str]]


def build_subagent_task_prompt(task: SubagentTask) -> str:
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

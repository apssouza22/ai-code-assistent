from typing import List, Optional, Dict, Any
from src.core.action import Action
from dataclasses import dataclass, field

@dataclass
class Turn:
    """Represents a single turn in the conversation history."""
    llm_output: str
    actions_executed: List[Action] = field(default_factory=list)
    env_responses: List[str] = field(default_factory=list)
    task_trajectories: Optional[Dict[str, Dict[str, Any]]] = None

    def to_dict(self) -> dict:
        """Convert turn to dictionary format."""
        result = {
            "llm_output": self.llm_output,
            "actions_executed": [action.to_dict() for action in self.actions_executed],
            "env_responses": self.env_responses
        }
        if self.task_trajectories:
            result["task_trajectories"] = self.task_trajectories

        return result

    def to_prompt(self) -> str:
        """Convert turn to prompt format for inclusion in state."""
        parts = []

        # Include LLM output (truncated if very long)
        if len(self.llm_output) > 500:
            parts.append(f"Agent: {self.llm_output[:500]}...")
        else:
            parts.append(f"Agent: {self.llm_output}")

        if self.env_responses:
            for response in self.env_responses:
                parts.append(f"Env: {response}")

        return "\n".join(parts)

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.action.actions import Action


@dataclass
class ExecutionResult:
    actions_executed: List[Action]
    env_responses: List[str]
    has_error: bool
    finish_message: Optional[str] = None
    done: bool = False
    task_trajectories: Optional[Dict[str, Dict[str, Any]]] = None

    def to_dict(self) -> dict:
        result = {
            "actions_executed": [a.to_dict() for a in self.actions_executed],
            "env_responses": self.env_responses,
            "has_error": self.has_error,
            "finish_message": self.finish_message,
            "done": self.done,
        }
        if self.task_trajectories is not None:
            result["task_trajectories"] = self.task_trajectories
        return result

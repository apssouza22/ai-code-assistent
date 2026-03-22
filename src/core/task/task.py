from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(Enum):
    CREATED = "created"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ContextBootstrapItem:
    path: str
    reason: str


@dataclass
class Task:
    task_id: str
    agent_name: str
    title: str
    description: str
    context_refs: List[str] = field(default_factory=list)
    context_bootstrap: List[ContextBootstrapItem] = field(default_factory=list)
    status: TaskStatus = TaskStatus.CREATED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["context_bootstrap"] = [
            {"path": item.path, "reason": item.reason} for item in self.context_bootstrap
        ]
        return d

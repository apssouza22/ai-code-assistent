"""Data types for subagent communication."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class ContextItem:
    """A single context item to be stored."""
    id: str
    content: str


@dataclass
class ReportMetadata:
    """Metadata for subagent execution."""
    trajectory: Optional[List[Dict[str, Any]]] = None
    num_turns: Optional[int] = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0


@dataclass
class SubagentReport:
    """Structured report from a subagent."""
    contexts: List[ContextItem]
    comments: str
    meta: Optional[ReportMetadata] = None

    def to_dict(self):
        """Convert to dictionary format expected by orchestrator hub."""
        result: Dict[str, Any] = {
            "contexts": [
                {"id": ctx.id, "content": ctx.content}
                for ctx in self.contexts
            ],
            "comments": self.comments
        }
        if self.meta:
            result["meta"] = {
                "trajectory": self.meta.trajectory,
                "num_turns": self.meta.num_turns
            }
        return result

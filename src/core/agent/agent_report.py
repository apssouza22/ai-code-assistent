import dataclasses
from typing import Any, Optional

from src.core.agent.subagent_report import ReportMetadata


@dataclasses.dataclass
class AgentReport:
    """Data structure for agent reports."""
    msg: str
    report_metadata: Optional[ReportMetadata] = None
    task: Optional[Any] = None
    metadata: Optional[dict[str, Any]] = None

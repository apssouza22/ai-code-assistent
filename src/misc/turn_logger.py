"""Turn-by-turn logger for orchestrator and subagent execution tracking."""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)


class SafeJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles non-serializable objects gracefully."""

    def default(self, obj):
        """Convert non-serializable objects to strings."""
        try:
            # Try the default encoder first
            return super().default(obj)
        except TypeError:
            # For any non-serializable object, convert to string representation
            return str(obj)


class TurnLogger:
    """Handles turn-by-turn logging for orchestrator and subagents."""

    @staticmethod
    def _sanitize_for_json(data: Any) -> Any:
        """Recursively sanitize data for JSON serialization."""
        if isinstance(data, dict):
            return {k: TurnLogger._sanitize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [TurnLogger._sanitize_for_json(item) for item in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        elif hasattr(data, '__dict__'):
            # For objects with __dict__, convert to dict representation
            return TurnLogger._sanitize_for_json(data.__dict__)
        else:
            # For everything else, convert to string
            return str(data)

    def __init__(self, logging_dir: Optional[Path], prefix: str):
        self.logging_dir = logging_dir
        self.prefix = prefix
        self.enabled = logging_dir is not None

        if self.enabled:
            self.logging_dir = Path(logging_dir)
            self.logging_dir.mkdir(exist_ok=True, parents=True)

    def log_turn(self, turn_num: int, data: Dict[str, Any]) -> Optional[Path]:
        if not self.enabled:
            return None

        sanitized_data = self._sanitize_for_json(data)
        sanitized_data["turn_number"] = turn_num
        sanitized_data["timestamp"] = datetime.now().isoformat()
        sanitized_data["prefix"] = self.prefix
        file_path = self.logging_dir / f"{self.prefix}_turn_{turn_num:03d}.json"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sanitized_data, f, indent=2, ensure_ascii=False, cls=SafeJSONEncoder)

            logger.debug(f"Logged turn {turn_num} to {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to log turn {turn_num}: {e}")
            return None

    def log_final_summary(self, data: Dict[str, Any], filename: str = "summary.json") -> Optional[Path]:
        if not self.enabled:
            return None

        sanitized_data = self._sanitize_for_json(data)
        sanitized_data["timestamp"] = datetime.now().isoformat()
        sanitized_data["prefix"] = self.prefix
        file_path = self.logging_dir / f"{self.prefix}_{filename}"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sanitized_data, f, indent=2, ensure_ascii=False, cls=SafeJSONEncoder)

            logger.info(f"Logged summary to {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to log summary: {e}")
            return None

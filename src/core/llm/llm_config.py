"""LLM configuration DTO."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LlmConfig:
    """Configuration for LLM calls, bundling model parameters."""
    model: str
    temperature: float = 0.7
    api_key: Optional[str] = None
    max_tokens: int = 4096

"""
Context module - Public API for context management.

This module provides a clean boundary for the context subsystem by exposing
only the classes and functions needed by external modules.
"""
from src.core.context.context import Context
from src.core.context.context_store import ContextStore

__all__ = [
    "Context",
    "ContextStore",
]


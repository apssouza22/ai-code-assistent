"""Interface for action handlers."""

from abc import ABC, abstractmethod
from typing import Tuple

from src.core.action.actions import Action


class ActionHandlerInterface(ABC):
    """Interface that all action handlers must implement."""

    @abstractmethod
    def handle(self, action: Action) -> Tuple[str, bool]:
        """Handle an action and return (response, is_error).

        Args:
            action: The action to handle

        Returns:
            Tuple of (formatted_response, is_error)
        """
        pass


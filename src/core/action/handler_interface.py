from abc import ABC, abstractmethod
from typing import Tuple

from src.core.action.actions import Action


class ActionHandlerInterface(ABC):

    @abstractmethod
    def handle(self, action: Action) -> Tuple[str, bool]:
        pass

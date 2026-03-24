from typing import Dict, Callable

from src.core.action.actions import BashAction, LSAction, GlobAction, GrepAction
from src.core.backend import CommandExecutor
from src.core.bash.bash_handlers import GrepActionHandler, GlobActionHandler, LSActionHandler, BashActionHandler


def get_bash_handlers(command_executor: CommandExecutor) -> Dict[type, Callable]:
    return {
        BashAction: BashActionHandler(command_executor).handle,
        GrepAction: GrepActionHandler(command_executor).handle,
        GlobAction: GlobActionHandler(command_executor).handle,
        LSAction: LSActionHandler(command_executor).handle,
    }

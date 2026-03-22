from typing import Dict

from src.core.context.context import Context


class ContextStore:

    def __init__(self):
        self.store: Dict[str, Context] = {}

    def add_context(self, key, context) -> None:
        self.store[key] = context

    def get_context(self, key):
        return self.store.get(key, None)

    def remove_context(self, key) -> None:
        if key in self.store:
            del self.store[key]

    def clear(self) -> None:
        self.store.clear()

    def get_all_contexts(self):
        return self.store.items()

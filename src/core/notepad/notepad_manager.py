"""State managers for todo and scratchpad functionality."""

from typing import List


class ScratchpadManager:
    """Manages scratchpad/notes for agent memory."""

    def __init__(self):
        self.notes: List[str] = []

    def add_note(self, content: str) -> int:
        """Add a note and return its index."""
        self.notes.append(content)
        return len(self.notes) - 1

    def view_all(self) -> str:
        """Return formatted view of all notes."""
        if not self.notes:
            return "Scratchpad is empty."

        lines = ["Scratchpad Contents:"]
        for i, note in enumerate(self.notes):
            lines.append(f"\n--- Note {i + 1} ---\n{note}")

        return "\n".join(lines)

    def reset(self):
        """Reset the scratchpad manager state."""
        self.notes.clear()

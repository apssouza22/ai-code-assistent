"""User input action handler."""

import sys
import select
from typing import Tuple

from src.core.action.actions import UserInputAction
from src.core.action.handler_interface import ActionHandlerInterface
from src.core.common.utils import format_tool_output


class UserInputActionHandler(ActionHandlerInterface):
    """Handler for requesting input from the user."""

    def handle(self, action: UserInputAction) -> Tuple[str, bool]:
        """Handle user input request."""
        try:
            # Display the prompt
            print(f"\n{'='*60}")
            print(f"USER INPUT REQUESTED")
            print(f"{'='*60}")
            print(f"{action.prompt}")

            # If options are provided, display them
            if action.options:
                print("\nPlease select one of the following options:")
                for idx, option in enumerate(action.options, 1):
                    print(f"  {idx}. {option}")
                print("\nEnter your choice (number or text): ", end='', flush=True)
            else:
                print("\nYour response: ", end='', flush=True)

            # Read user input with timeout
            user_input = self._read_input_with_timeout(action.timeout_secs)

            if user_input is None:
                error_msg = f"[ERROR] User input timed out after {action.timeout_secs} seconds"
                return format_tool_output("user_input", error_msg), True

            # Validate input
            if not user_input.strip() and not action.allow_empty:
                error_msg = "[ERROR] Empty input not allowed"
                return format_tool_output("user_input", error_msg), True

            # If options were provided, validate the selection
            if action.options:
                # Try to parse as number
                try:
                    choice_idx = int(user_input.strip()) - 1
                    if 0 <= choice_idx < len(action.options):
                        selected = action.options[choice_idx]
                        response = f"User selected: {selected}"
                        return format_tool_output("user_input", response), False
                except ValueError:
                    pass

                # Check if input matches any option (case-insensitive)
                user_input_lower = user_input.strip().lower()
                for option in action.options:
                    if option.lower() == user_input_lower:
                        response = f"User selected: {option}"
                        return format_tool_output("user_input", response), False

                # Invalid selection
                error_msg = f"[ERROR] Invalid selection: '{user_input}'. Please choose from the provided options."
                return format_tool_output("user_input", error_msg), True

            # Free text input
            response = f"User input: {user_input.strip()}"
            return format_tool_output("user_input", response), False

        except Exception as e:
            error_msg = f"[ERROR] Failed to read user input: {str(e)}"
            return format_tool_output("user_input", error_msg), True

    def _read_input_with_timeout(self, timeout_secs: int) -> str | None:
        """Read input from user with a timeout.

        Args:
            timeout_secs: Timeout in seconds

        Returns:
            User input string or None if timeout
        """
        # Check if stdin is available (for non-interactive environments)
        if not sys.stdin.isatty():
            # In non-interactive mode, just read without timeout
            try:
                return input()
            except EOFError:
                return None

        # For Unix-like systems with terminal
        if hasattr(select, 'select'):
            # Use select for timeout on Unix-like systems
            ready, _, _ = select.select([sys.stdin], [], [], timeout_secs)
            if ready:
                return sys.stdin.readline().rstrip('\n')
            return None
        else:
            # Fallback for Windows or systems without select
            # Note: This doesn't support timeout on Windows
            try:
                return input()
            except EOFError:
                return None


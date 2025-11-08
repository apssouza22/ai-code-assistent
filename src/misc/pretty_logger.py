"""Pretty colored terminal logger for better visibility."""

from datetime import datetime
from typing import Optional

class Colors:
    """ANSI color codes for terminal output."""
    # Basic colors
    RESET = "\033[0m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"


class PrettyLogger:
    """Pretty terminal logger with colored output."""

    PRINT_DEBUG = False

    @staticmethod
    def _get_timestamp() -> str:
        """Get formatted timestamp."""
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def info(message: str, agent_name: Optional[str] = None):
        """Print action comment in yellow.

        Args:
            message: The comment text
            agent_name: Optional agent name to include
        """
        timestamp = PrettyLogger._get_timestamp()
        if agent_name:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] "
                  f"{Colors.BLUE}{agent_name}{Colors.RESET} - "
                  f"{Colors.CYAN}{message}{Colors.RESET}")
        else:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] "
                  f"{Colors.CYAN}{message}{Colors.RESET}")


    @staticmethod
    def debug(message: str, agent_name: Optional[str] = None):
        """Print action response with timestamp (as specified by user).

        Args:
            message: The response message
            agent_name: Optional agent name to include
        """
        if not PrettyLogger.PRINT_DEBUG:
            return
        timestamp = PrettyLogger._get_timestamp()
        if agent_name:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] "
                  f"{Colors.BLUE}{agent_name}{Colors.RESET} - "
                  f"{Colors.BRIGHT_BLACK}{message}{Colors.RESET}")
        else:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] "
                  f"{Colors.BRIGHT_BLACK}{message}{Colors.RESET}")

    @staticmethod
    def success(message: str, agent_name: Optional[str] = None):
        """Print success message in green.

        Args:
            message: Success message
            agent_name: Optional agent name to include
        """
        timestamp = PrettyLogger._get_timestamp()
        if agent_name:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] "
                  f"{Colors.BLUE}{agent_name}{Colors.RESET} - "
                  f"{Colors.GREEN}{message}{Colors.RESET}")
        else:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] "
                  f"{Colors.GREEN}{message}{Colors.RESET}")

    @staticmethod
    def error(message: str, agent_name: Optional[str] = None):
        """Print error message in red.

        Args:
            message: Error message
            agent_name: Optional agent name to include
        """
        timestamp = PrettyLogger._get_timestamp()
        if agent_name:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] "
                  f"{Colors.BLUE}{agent_name}{Colors.RESET} - "
                  f"{Colors.RED}{message}{Colors.RESET}")
        else:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] "
                  f"{Colors.RED}{message}{Colors.RESET}")

    @staticmethod
    def warning(message: str, agent_name: Optional[str] = None):
        """Print warning message in yellow.

        Args:
            message: Warning message
            agent_name: Optional agent name to include
        """
        timestamp = PrettyLogger._get_timestamp()
        if agent_name:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] "
                  f"{Colors.BLUE}{agent_name}{Colors.RESET} - "
                  f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")
        else:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] "
                  f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")

    @staticmethod
    def section_header(title: str, char: str = "="):
        """Print a section header.

        Args:
            title: Section title
            char: Character to use for the line
        """
        timestamp = PrettyLogger._get_timestamp()
        line = char * 120
        print(f"\n{Colors.BRIGHT_WHITE}{line}")
        print(f"[{Colors.BRIGHT_BLACK}{timestamp}{Colors.BRIGHT_WHITE}] {Colors.BOLD}{Colors.CYAN}{title}{Colors.RESET}")
        print(f"{Colors.BRIGHT_WHITE}{line}{Colors.RESET}\n")

    @staticmethod
    def separator(char: str = "-", length: int = 60):
        """Print a separator line.

        Args:
            char: Character to use
            length: Length of the line
        """
        print(f"{Colors.BRIGHT_BLACK}{char * length}{Colors.RESET}")


# Convenience instance
pretty_log = PrettyLogger()


# Example usage
if __name__ == "__main__":
    print("\n=== Testing Pretty Logger ===\n")

    pretty_log.section_header("Agent Execution Test")
    pretty_log.success("Task completed successfully!", "ORCHESTRATOR")

    pretty_log.separator()
    pretty_log.warning("File size exceeds recommended limit", "SUBAGENT")

    pretty_log.separator()

    pretty_log.error("Failed to parse action", "ORCHESTRATOR")
    pretty_log.info("Retrying with fallback parser...")
    pretty_log.debug("Debug info: action_type=unknown")

    print("\n=== Test Complete ===\n")


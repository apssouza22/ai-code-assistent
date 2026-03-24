"""Command execution abstraction for both Docker and Tmux environments."""

import subprocess
import time
import uuid
from abc import ABC, abstractmethod
from typing import Tuple

from src.misc import pretty_log


class CommandExecutor(ABC):
    """Abstract base class for command execution in different environments."""

    @abstractmethod
    def execute(self, cmd: str, timeout: int = 30) -> Tuple[str, int]:
        """Execute a command and return (output, return_code)."""

    @abstractmethod
    def execute_background(self, cmd: str) -> None:
        """Execute a command in background."""


class DockerExecutor(CommandExecutor):
    """Execute commands using docker exec."""

    def __init__(self, container_name: str):
        self.container_name = container_name

    def execute(self, cmd: str, timeout: int = 30) -> Tuple[str, int]:
        """Execute a command in the Docker container and return (output, return_code)."""
        try:
            proc = subprocess.Popen(
                ['docker', 'exec', self.container_name, 'bash', '-c', cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )

            try:
                stdout, _ = proc.communicate(timeout=timeout)
                output = stdout.decode('utf-8', errors='replace')
                exit_code = proc.returncode or 0
                return output, exit_code
            except subprocess.TimeoutExpired:
                proc.kill()
                return f"Command timed out after {timeout} seconds", 124  # 124 is the standard timeout exit code

        except Exception as e:
            return f"Error executing command: {str(e)}", 1

    def execute_background(self, cmd: str) -> None:
        """Execute a command in background in the Docker container."""
        try:
            subprocess.Popen(
                ['docker', 'exec', '-d', self.container_name, 'bash', '-c', cmd]
            )
        except Exception:
            # Background execution failures are silently ignored
            pass


def get_docker_executor() -> CommandExecutor:
    container_name = f"container_executor_{uuid.uuid4().hex[:8]}"
    pretty_log.info(f"Starting Docker container: {container_name}")
    subprocess.run([
        'docker', 'run', '-d', '--rm',
        '--name', container_name,
        'ubuntu:latest',
        'sleep', 'infinity'
    ], check=True, capture_output=True)

    # Wait for container to be ready
    time.sleep(2)

    executor = DockerExecutor(container_name)
    executor.execute("mkdir /workspace")
    return executor

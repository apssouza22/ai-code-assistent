#!/usr/bin/env python3
"""Test script for Subagent with real LiteLLM calls."""

import logging
import os
import subprocess
import sys
import time
import uuid

from src.core.action.actions import BashAction, ReportAction
from src.core.bash.bash_handler import BashActionHandler
from src.core.action.handlers.report_handler import ReportActionHandler
from src.core.agent import Subagent, SubagentTask
from src.core.bash import DockerExecutor

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))



logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_subagent_file_creation(model: str, temperature=0.1):
    """Test subagent with a simple file creation task."""

    print(f"\n{'='*60}")
    print(f"Testing with model: {model}")
    print(f"Temperature: {temperature}")
    print('='*60)

    # Generate unique container name
    container_name = f"test_subagent_{uuid.uuid4().hex[:8]}"

    try:
        # Start Docker container
        print(f"Starting Docker container: {container_name}")
        subprocess.run([
            'docker', 'run', '-d', '--rm',
            '--name', container_name,
            'ubuntu:latest',
            'sleep', 'infinity'
        ], check=True, capture_output=True)

        # Wait for container to be ready
        time.sleep(2)

        # Create work directory in container
        subprocess.run([
            'docker', 'exec', container_name,
            'mkdir', '-p', '/workspace'
        ], check=True)

        # Create command executor with Docker
        executor = DockerExecutor(container_name)

        # Change to workspace directory in container
        executor.execute("cd /workspace")

        # Create minimal actions dictionary for the test
        actions = {
            BashAction: BashActionHandler(executor).handle,
            ReportAction: ReportActionHandler().handle,
        }

        # Create task
        instructions = ("Create a file called \"hello.txt\" in /workspace with the exact content " \
                     "\"Hello, world!\" followed by a newline character.\n\n" \
                     "Requirements:\n" \
                     "- File must be named exactly \"hello.txt\" in /workspace\n" \
                     "- Content must be exactly \"Hello, world!\" with a newline at the end\n" \
                     "- Do not create any other files or folders\n" \
                     "- Verify the file was created correctly by reading it back\n\n" \
                     "Please confirm successful creation by showing the file contents and " \
                     "verifying it ends with a newline.")
        task = SubagentTask(
            agent_name="coder",
            title="Create hello.txt with content",
            description=instructions,
            instruction=instructions,
            task_id=f"test_task_{uuid.uuid4().hex[:8]}",
            task_context={},
            bootstrap_ctx=[],
        )

        # Create subagent with specified model
        subagent = Subagent(
            agent_name="coder",
            actions=actions,
            max_turns=10,
            model=model,
            temperature=temperature,
        )

        # Run the task
        print("\nExecuting task...")
        report = subagent.run_task(task)

        # Display results
        print(f"\n{'='*40}")
        print("REPORT:")
        print(f"{'='*40}")
        print(f"Comments: {report.comments}")
        print(f"\nContexts ({len(report.contexts)}):")
        for ctx in report.contexts:
            print(f"  - {ctx.id}: {ctx.content[:100]}..."
                  if len(ctx.content) > 100 else f"  - {ctx.id}: {ctx.content}")

        # Check if file was created in container
        output, exit_code = executor.execute("cat /workspace/hello.txt")
        if exit_code == 0:
            print(f"\n✓ File created successfully in container!")
            print(f"  Content: {repr(output)}")
            if output == "Hello, world!\n":
                print("  ✓ Content matches expected value exactly")
            else:
                print("  ✗ Content does not match expected value")
        else:
            print("\n✗ File was not created in container")

        # Show trajectory summary
        if report.meta and report.meta.trajectory:
            print(f"\nTrajectory: {len(report.meta.trajectory)} messages")
            # Subtract system and initial user message
            print(f"  Turns taken: {(len(report.meta.trajectory) - 2) // 2}")

        return report

    finally:
        # Clean up Docker container
        try:
            print(f"\nStopping and removing container: {container_name}")
            subprocess.run(['docker', 'stop', container_name],
                         capture_output=True, timeout=10)
        except Exception as e:
            print(f"Error cleaning up container: {e}")


def main():
    """Main test runner."""

    # Test with different models if you want
    models_to_test = [
        ("openai/gpt-5-mini-2025-08-07", 1),
        # ("anthropic/claude-sonnet-4-20250514", 0.1),
        # ("openai/gpt-5-2025-08-07", 1),
        # ("openrouter/qwen/qwen3-coder", 0.1),
        # ("openrouter/z-ai/glm-4.5", 0.1),
        # ("openrouter/deepseek/deepseek-chat-v3.1", 0.1),
    ]

    # Check for environment variables
    if not os.getenv("LITE_LLM_API_KEY") and not os.getenv("LITELLM_API_KEY"):
        print("Warning: No API key found in LITE_LLM_API_KEY or LITELLM_API_KEY")
        print("You may need to set one of these environment variables")

    results = []
    for model, temp in models_to_test:
        try:
            report = test_subagent_file_creation(model=model, temperature=temp)
            results.append((model, "SUCCESS", report))
        except Exception as e:
            print(f"\n✗ Error with model {model}: {e}")
            results.append((model, "FAILED", str(e)))

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    for model, status, _ in results:
        print(f"{model}: {status}")


if __name__ == "__main__":
    main()

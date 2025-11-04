#!/usr/bin/env python3
"""Test script for LeadArchitectAgent with real LiteLLM calls."""

import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from src.core.agent import AgentTask
from src.core.orchestrator.factory import create_orchestrator_agent
from src.core.bash import DockerExecutor
from src.misc import pretty_log

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def lead_architect_simple_task(model: str, temperature=0.1):
    """Test orchestrator with a simple task."""

    print(f"\n{'=' * 60}")
    print(f"Testing with model: {model}")
    print(f"Temperature: {temperature}")
    print('=' * 60)

    # Generate unique container name
    container_name = f"test_orchestrator_{uuid.uuid4().hex[:8]}"

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

        executor = DockerExecutor(container_name)
        executor.execute("mkdir /workspace")
        executor.execute("cd /workspace")
        this_dir_path: Path = Path(__file__).parent.resolve()
        logging_dir = Path(this_dir_path) / "tracing_logs"
        try:
            orchestrator = create_orchestrator_agent(
                api_key=os.getenv("LITE_LLM_API_KEY") or os.getenv("LITELLM_API_KEY"),
                temperature=temperature,
                container_name=container_name,
                command_executor=executor,
                logging_dir=logging_dir
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

        instruction = (
            "Create a file called 'hello.txt' with content 'Hello world! Ending with a newline.' "
        )

        # Run the task
        agent_task = AgentTask(task_id="test_task", instruction=instruction, agent_name="orchestrator")
        result = orchestrator.run_task(agent_task, max_turns=15)


        pretty_log.section_header("EXECUTION RESULT:")
        pretty_log.success(f"Completed: {result['completed']}")
        pretty_log.success(f"Finish message: {result['finish_message']}")
        pretty_log.success(f"Turns executed: {result['turns_executed']}")
        pretty_log.success(f"Max turns reached: {result['max_turns_reached']}")

        # Show final state summary
        if orchestrator.session_history:
            pretty_log.section_header("FINAL STATE:")
            pretty_log.debug(f"{orchestrator.session_history.to_dict()}")

        # Check if files were created in container
        pretty_log.section_header("VERIFICATION:")

        # Check hello.txt
        output, exit_code = executor.execute("cat hello.txt")
        if exit_code == 0:
            pretty_log.success(f"✓ hello.txt created successfully!")
            pretty_log.success(f"  Content: {repr(output)}")
            if output.endswith('\n'):
                pretty_log.success("  Content ends with a newline.")
            else:
                pretty_log.success("  Content does NOT end with a newline.")
        else:
            pretty_log.warning("✗ hello.txt was not created")

        # Show final state summary
        if orchestrator.session_history:
            pretty_log.section_header("FINAL STATE:")
            pretty_log.debug(f"{orchestrator.session_history.to_dict()}")

        return result

    finally:
        # Clean up Docker container
        try:
            print(f"\nStopping and removing container: {container_name}")
            subprocess.run(['docker', 'stop', container_name], capture_output=True, timeout=10)
        except Exception as e:
            print(f"Error cleaning up container: {e}")


def main():
    """Main test runner."""

    # Test with different models if you want
    models_to_test = [
        ("openai/gpt-5-mini-2025-08-07", 1),
        # ("openai/gpt-5-2025-08-07", 1),
        # ("anthropic/claude-sonnet-4-20250514", 0.1),
        # ("openrouter/qwen/qwen3-coder", 0.1),
        # ("openrouter/z-ai/glm-4.5", 0.1),
        # ("openrouter/deepseek/deepseek-chat-v3.1", 0.1),
    ]

    # Check for environment variables
    if not os.getenv("LITE_LLM_API_KEY") and not os.getenv("LITELLM_API_KEY"):
        print("Warning: No API key found in LITE_LLM_API_KEY or LITELLM_API_KEY")
        print("You may need to set one of these environment variables")

    print("\n" + "=" * 60)
    print("TESTING LEAD ARCHITECT AGENT")
    print("=" * 60)

    # Test 1: Simple task
    print("\n### TEST 1: Simple File Creation ###")
    results = []
    for model, temp in models_to_test:
        try:
            result = lead_architect_simple_task(model=model, temperature=temp)
            results.append((model, "Test 1", "SUCCESS", result))
        except Exception as e:
            print(f"\n✗ Error with model {model}: {e}")
            results.append((model, "Test 1", "FAILED", str(e)))

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print('=' * 60)
    for model, test_name, status, _ in results:
        print(f"{model} - {test_name}: {status}")

#
if __name__ == "__main__":
    main()

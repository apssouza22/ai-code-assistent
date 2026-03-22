# Agentic Code assistant using Deepagent-style

This is an experimental project implementing an agentic code assistant inspired by Deepagent-style architectures.
Deep Agents are an advanced agent architecture designed for handling complex, multi-step tasks that require sustained
reasoning, tool use, and memory.
Unlike traditional agents that operate in short loops or perform simple tool calls, Deep Agents plan their actions,
manage evolving context, delegate subtasks to specialized sub-agents, and maintain state across long interactions. This
architecture is already powering real-world applications like Claude Code, Deep Research, and Manus.
It features a central orchestrator agent that coordinates specialised subagents (explorers and coders) to tackle complex
software tasks through strategic delegation, verification, and knowledge sharing.


## System Architecture Overview

<img src="readme_imgs/architecture-diag.png" alt="System architecture overview" width="600"/>


## Getting started

Ensure you set the `LITE_LLM_API_KEY` environment variable. The default model is `openai/gpt-4o`.

For dev:

```bash
cp .env.local .env
uv venv
source .venv/bin/activate
uv sync
uv pip install -e ".[dev]" 
python src/main.py
```

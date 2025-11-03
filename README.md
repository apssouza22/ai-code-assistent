# Agentic Code assistant using Deepagent-style
This is an experimental project implementing an agentic code assistant inspired by Deepagent-style architectures. 
It features a central orchestrator agent that coordinates specialised subagents (explorers and coders) to tackle complex software tasks through strategic delegation, verification, and knowledge sharing.

## How the System Works

![System architecture overview](readme_imgs/orch_agent_sys_arch.png)

The orchestrator acts as the brain of the operation - it receives the user's task but never touches code directly. Instead, it:

1. **Analyses** the task and breaks it into focused subtasks
2. **Dispatches** explorer agents to understand the system
3. **Delegates** implementation work to coder agents with precise instructions
4. **Verifies** all changes through additional explorer agents
5. **Maintains** the context store with all discovered knowledge

The orchestrator's lack of direct code access forces proper delegation and verification patterns, leading to more strategic solutions.

For a full breakdown of this project's code structure, see [here](./PROJECT_STRUCTURE.md)

## 🤖 The Agents

While all agents use the same underlying LLM, each operates with its own context window, specialised system message, and distinct toolset. This creates functionally different agents optimised for their specific roles.

### 🎯 Orchestrator Agent
[System message](src/system_msgs/md_files/orchestrator_sys_msg_v0.1.md)
**Role:** Strategic coordinator and persistent intelligence layer  
**Capabilities:** Task decomposition, context management, subagent delegation  
**Tools:** Task creation, subagent launching, context store management  
**Restrictions:** Cannot read or modify code directly - operates purely at architectural level  

The orchestrator maintains the complete picture across all tasks, tracking discoveries and progress. It crafts precise task descriptions that explicitly specify what contexts subagents should return, ensuring focused and valuable information gathering.

**Trust Calibration Strategy:**  
The orchestrator employs adaptive delegation based on task complexity:
- **Low Complexity Tasks**: Grants extremely high autonomy to the coder agent for simple modifications and bug fixes
- **Medium/Large Tasks**: Maintains strong trust but uses iterative decomposition - breaking complex problems into atomic, verifiable steps
- **Verification Philosophy**: Uses explorer agents liberally to verify progress, especially when tasks involve critical functionality


### 🔍 Explorer Agent 
[System message](src/system_msgs/md_files/explorer_sys_msg_v0.1.md) 
**Role:** Read-only investigation and verification specialist  
**Capabilities:** System exploration, code analysis, test execution, verification  
**Tools:** File reading, search operations (grep/glob), bash commands, temporary script creation  
**Restrictions:** Cannot modify existing files - strictly read-only operations  

Explorers gather intelligence about the codebase, verify implementations, and discover system behaviors. They create knowledge artifacts that eliminate redundant exploration for future agents.

### 💻 Coder Agent
[System message](src/system_msgs/md_files/coder_sys_msg_v0.1.md)
**Role:** Implementation specialist with write access  
**Capabilities:** Code creation/modification, refactoring, bug fixes, system changes  
**Tools:** Full file operations (read/write/edit), bash commands, search operations  
**Restrictions:** None - full system access for implementation tasks  

Coders transform architectural vision into working code. They receive focused tasks with relevant contexts and implement solutions while maintaining code quality and conventions.

## Key System Components

### 🧠 Smart Context Sharing

#### How Context Sharing Works

I introduced a novel approach to multi-agent coordination through the **Context Store** - a persistent knowledge layer that transforms isolated agent actions into coherent problem-solving. Unlike traditional multi-agent systems where agents operate in isolation, my architecture enables sophisticated knowledge accumulation and sharing.

**The Context Store Pattern:**
1. **Orchestrator-Directed Discovery**: The orchestrator explicitly specifies what contexts it needs from each subagent, ensuring focused and relevant information gathering and implementation reporting
2. **Knowledge Artifacts**: Subagents create discrete, reusable context items based on the orchestrator's requirements
3. **Persistent Memory**: Contexts persist across agent interactions, building a comprehensive system understanding
4. **Selective Injection**: The orchestrator precisely injects relevant contexts into new tasks, eliminating redundant discovery and providing all the information a subagent needs to complete it's respective task
5. **Compound Intelligence**: Each action builds meaningfully on previous discoveries, creating exponential problem-solving capability

**Key Benefits:**
- **Eliminates Redundant Work**: Subagents never need to rediscover the same information twice
- **Reduces Context Window Load**: Agents receive only the specific contexts they need
- **Enables Complex Solutions**: Multi-step problems that no single agent could solve become tractable
- **Maintains Focus**: Each subagent operates with a clean, focused context window

This architecture ensures that every piece of discovered information becomes a permanent building block for future tasks, creating a system that genuinely learns and adapts throughout the problem-solving process.

### 📋 Task Management

The orchestrator maintains a comprehensive task management system that tracks all subagent activities:

**Core Functions:**
- **Progress Tracking**: Monitors task status (pending, completed, failed) across potentially hundreds of coordinated actions
- **Failure Recovery**: Captures failure reasons to enable strategic adaptation and intelligent retries
- **Workflow Orchestration**: Maintains clear audit trails of what's been attempted, preventing redundant work
- **Strategic Planning**: Enables systematic decomposition of complex problems into verifiable subtasks

The task manager serves as the orchestrator's operational memory - while the context store holds discovered knowledge, the task manager tracks the journey of discovery itself. This dual-layer system ensures the orchestrator always knows both what it has learned AND how it learned it, enabling sophisticated multi-step solutions that build intelligently on previous attempts.

## Getting started

For dev:
```bash
uv sync
uv pip install -e ".[dev]" 
```

To quickly test various models: See [/test](./test/)

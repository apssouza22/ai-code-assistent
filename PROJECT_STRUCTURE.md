# Project Structure Documentation
This document provides an overview of the architecture and key components of the multi-agent orchestration system designed for codebase tasks. 
The system consists of an Orchestrator agent that manages high-level tasks and multiple specialized Subagents (Explorer and Coder) that execute delegated tasks. The architecture emphasizes modularity, extensibility, and robust interaction with a codebase environment.

## Core Components

### 1. **OrchestratorAgent** (`src/core/orchestrator/orchestrator_agent.py`)
The main coordinator agent that manages the entire task execution workflow.

**Key Responsibilities:**
- Receives high-level task instructions
- Manages conversation history and session state
- Creates and delegates tasks to sub-agents
- Processes sub-agent reports and maintains context store
- Tracks token usage across all agents


### 2. **Subagent** (`src/agent/subagent.py`)
Specialized agents (Explorer or Coder) that execute specific delegated tasks.

**Types:**
- **Explorer Agent**: Investigates codebase, searches for information
- **Coder Agent**: Implements features, fixes bugs, writes code

**Key Features:**
- Autonomous execution within defined scope
- Context collection and reporting back to orchestrator
- Forced reporting mechanism when max turns reached
- Independent state management

### 3. **TaskStore & ContextStore**
Core data stores for task and context management.

**TaskStore** (`src/core/task/task_store.py`):
- Creates and tracks tasks throughout their lifecycle
- Maintains task status and metadata
- Provides task summaries and history

**ContextStore** (`src/core/context/context_store.py`):
- Centralized storage for discovered information
- Stores contexts with unique IDs for reference
- Enables knowledge sharing across agent boundaries

**Data Flow:**
1. Orchestrator creates tasks with context references
2. Subagents execute tasks and return reports with contexts
3. Orchestrator stores contexts in ContextStore for future reference
4. Contexts are shared across subagents via direct store access

### 4. **Action System** (`src/core/action/`)
Comprehensive action framework for agent-environment interaction.

**Action Categories:**
- **File Operations**: Read, Write, Edit, MultiEdit
- **Search Operations**: Grep, Glob, LS
- **Task Management**: TaskCreate, LaunchSubagent, Report
- **State Management**: Todo operations, Scratchpad notes
- **Environment**: Bash command execution
- **Control**: Finish action for task completion

**Parser Pipeline:**
1. XML tag extraction from LLM response
2. YAML content parsing within tags
3. Pydantic validation and action object creation
4. Action execution via handlers

## Key Architecture Patterns

### 1. **Multi-Agent Orchestration Pattern**
The system employs a hierarchical multi-agent architecture where:
- **Orchestrator** acts as the coordinator
- **Subagents** are specialized workers for specific task types
- Communication happens through structured reports and context sharing

### 2. **Stateless Turn-Based Execution**
Each agent operates in discrete turns:
- LLM generates actions based on current state
- Actions are parsed and executed
- Environment responses update the state
- Process repeats until task completion or max turns

### 3. **Context Store Pattern**
Centralized information management:
- Subagents discover and report contexts
- TaskManager stores contexts in ContextStore with unique IDs
- Future tasks can reference stored contexts
- Enables knowledge sharing across agent boundaries

### 4. **Action-First Design**
All agent capabilities are expressed as discrete actions:
- Declarative action definitions using Pydantic models
- XML-based action syntax in LLM responses
- Strict validation before execution
- Clear separation between parsing and execution

### 5. **Forced Completion Pattern**
Ensures task termination:
- Max turn limits for both orchestrator and subagents
- Forced reporting mechanism when limits reached
- Fallback report generation if agent fails to comply
- Prevents infinite loops and resource exhaustion

### 6. **Token Tracking Architecture**
Comprehensive token usage monitoring:
- Each agent tracks its own message history
- Token counting at orchestrator and subagent levels
- Aggregated reporting for total system usage
- Supports both input and output token metrics

### 7. **Pluggable Subagent Types**
Flexible subagent specialization:
- Easily extendable to add new subagent types
- Each type has tailored prompts and capabilities
- Orchestrator can launch different subagent types based on task needs

### 8. **Structured Logging Pattern**
Comprehensive logging and observability:
- Turn-based logging for debugging
- Separate log files for orchestrator and subagents
- JSON-formatted conversation logs
- Timestamped markers for performance analysis

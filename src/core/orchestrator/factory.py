from pathlib import Path
from typing import Optional, Dict, Callable

from src.core.action import TaskCreateAction
from src.core.action.actions import LaunchSubagentAction, BatchTodoAction, AddNoteAction, ViewAllNotesAction, FinishAction, ReportAction, BashAction, GrepAction, GlobAction, LSAction, ReadAction, \
  WriteAction, WriteTempScriptAction, AddContextAction, MultiEditAction, FileMetadataAction, EditAction
from src.core.action.handlers import FinishActionHandler, ReportActionHandler
from src.core.common.middleware import (
    AuditLogMiddleware, OutputTruncationMiddleware, PermissionMiddleware, TimingMiddleware,
    TurnLoggingMiddleware, TokenBudgetMiddleware, ErrorRecoveryMiddleware,
)
from src.core.agent import AgentManager, Subagent
from src.core.bash import CommandExecutor, DockerExecutor, FileManager, SearchManager
from src.core.bash.bash_handler import BashActionHandler
from src.core.bash.search_handlers import LSActionHandler, GlobActionHandler, GrepActionHandler
from src.core.context import ContextStore
from src.core.context.context_handler import AddContextActionHandler
from src.core.file.file_handlers import ReadActionHandler, WriteActionHandler, EditActionHandler, MultiEditActionHandler, FileMetadataActionHandler, WriteTempScriptActionHandler
from src.core.llm import LlmConfig
from src.core.notepad import AddNoteActionHandler, ViewAllNotesActionHandler
from src.core.notepad.notepad_manager import ScratchpadManager
from src.core.orchestrator.orchestrator_agent import OrchestratorAgent
from src.core.task import create_task_manager, TaskStore
from src.core.task.create_task_handler import CreateTaskActionHandler
from src.core.task.subagent_handler import LaunchSubagentActionHandler
from src.core.task.subagent_luncher import AgentLauncher
from src.core.todo.todo_handler import BatchTodoActionHandler
from src.core.todo.todo_manager import TodoManager
from src.system_msgs.system_msg_loader import load_explorer_system_message, load_coder_system_message, \
  load_orchestrator_system_message

ORCHESTRATOR_MODEL = "openai/gpt-4.1-2025-04-14"
SUBAGENT_MODEL = "openai/gpt-4.1-2025-04-14"

ORCHESTRATOR_TOKEN_BUDGET = 120_000
SUBAGENT_TOKEN_BUDGET = 90_000
ACTION_OUTPUT_MAX_CHARS = 30_000

EXPLORER_ALLOWED_ACTIONS = {
    FinishAction, ReportAction, BashAction,
    GrepAction, GlobAction, LSAction,
    ReadAction, FileMetadataAction,
    AddNoteAction, ViewAllNotesAction, BatchTodoAction,
    AddContextAction, WriteTempScriptAction,
}

CODER_ALLOWED_ACTIONS = {
    FinishAction, ReportAction, BashAction,
    GrepAction, GlobAction, LSAction,
    ReadAction, WriteAction, EditAction, MultiEditAction, FileMetadataAction,
    AddNoteAction, ViewAllNotesAction, BatchTodoAction,
    AddContextAction, WriteTempScriptAction,
}


def create_orchestrator_agent(
    api_key: str,
    container_name: str,
    command_executor: Optional[CommandExecutor] = None,
    logging_dir: Optional[Path] = None,
) -> OrchestratorAgent:
  """Factory function to create an OrchestratorAgent instance."""

  if command_executor is None:
    command_executor = DockerExecutor(container_name)

  subagent_llm_config = LlmConfig(model=SUBAGENT_MODEL, temperature=1, api_key=api_key)
  orchestrator_llm_config = LlmConfig(model=ORCHESTRATOR_MODEL, temperature=1, api_key=api_key)

  task_store = TaskStore()
  todo_manager = TodoManager()
  scratchpad_manager = ScratchpadManager()
  context_store = ContextStore()
  file_manager = FileManager(command_executor)
  search_manager = SearchManager(command_executor)

  actions = get_sub_agent_actions(command_executor, context_store, file_manager, scratchpad_manager, search_manager, todo_manager)

  explorer_middlewares = [
      TurnLoggingMiddleware(),
      ErrorRecoveryMiddleware(),
      TokenBudgetMiddleware(max_tokens=SUBAGENT_TOKEN_BUDGET, model=SUBAGENT_MODEL),
      AuditLogMiddleware(agent_name="explorer"),
      TimingMiddleware(),
      PermissionMiddleware(allowed_actions=EXPLORER_ALLOWED_ACTIONS, agent_name="explorer"),
      OutputTruncationMiddleware(max_chars=ACTION_OUTPUT_MAX_CHARS),
  ]

  coder_middlewares = [
      TurnLoggingMiddleware(),
      ErrorRecoveryMiddleware(),
      TokenBudgetMiddleware(max_tokens=SUBAGENT_TOKEN_BUDGET, model=SUBAGENT_MODEL),
      AuditLogMiddleware(agent_name="coder"),
      TimingMiddleware(),
      PermissionMiddleware(allowed_actions=CODER_ALLOWED_ACTIONS, agent_name="coder"),
      OutputTruncationMiddleware(max_chars=ACTION_OUTPUT_MAX_CHARS),
  ]

  explorer_agent = Subagent(
      system_prompt=load_explorer_system_message(),
      actions=actions,
      agent_name="explorer",
      llm_config=subagent_llm_config,
      logging_dir=logging_dir,
      middlewares=explorer_middlewares,
  )

  coder_agent = Subagent(
      system_prompt=load_coder_system_message(),
      actions=actions,
      agent_name="coder",
      llm_config=subagent_llm_config,
      logging_dir=logging_dir,
      middlewares=coder_middlewares,
  )

  agent_manager = AgentManager(
      agents=[explorer_agent, coder_agent],
  )
  task_manager = create_task_manager(
      task_store=task_store,
      context_store=context_store,
  )
  agent_launcher = AgentLauncher(
      agent_manager=agent_manager,
      task_manager=task_manager,
      context_store=context_store,
      file_manager=file_manager,
      search_manager=search_manager
  )

  create_task_action_handler = CreateTaskActionHandler(task_manager, agent_launcher)
  lunch_subagent_action_handler = LaunchSubagentActionHandler(agent_launcher)
  orchestrator_action_handlers = {**actions, TaskCreateAction: create_task_action_handler.handle, LaunchSubagentAction: lunch_subagent_action_handler.handle}

  orchestrator_middlewares = [
      TurnLoggingMiddleware(),
      ErrorRecoveryMiddleware(),
      TokenBudgetMiddleware(max_tokens=ORCHESTRATOR_TOKEN_BUDGET, model=ORCHESTRATOR_MODEL),
      AuditLogMiddleware(agent_name="orchestrator"),
      TimingMiddleware(),
      OutputTruncationMiddleware(max_chars=ACTION_OUTPUT_MAX_CHARS),
  ]

  return OrchestratorAgent(
      system_prompt=load_orchestrator_system_message(),
      actions=orchestrator_action_handlers,
      task_manager=task_manager,
      task_store=task_store,
      context_store=context_store,
      llm_config=orchestrator_llm_config,
      logging_dir=logging_dir,
      middlewares=orchestrator_middlewares,
  )


def get_sub_agent_actions(
    command_executor, context_store, file_manager, scratchpad_manager, search_manager, todo_manager
) -> Dict[type, Callable]:
  return {
    FinishAction: FinishActionHandler().handle,
    ReportAction: ReportActionHandler().handle,
    BashAction: BashActionHandler(command_executor).handle,
    GrepAction: GrepActionHandler(search_manager).handle,
    GlobAction: GlobActionHandler(search_manager).handle,
    LSAction: LSActionHandler(search_manager).handle,
    ReadAction: ReadActionHandler(file_manager).handle,
    WriteAction: WriteActionHandler(file_manager).handle,
    AddNoteAction: AddNoteActionHandler(scratchpad_manager).handle,
    ViewAllNotesAction: ViewAllNotesActionHandler(scratchpad_manager).handle,
    BatchTodoAction: BatchTodoActionHandler(todo_manager).handle,
    AddContextAction: AddContextActionHandler(context_store).handle,
    WriteTempScriptAction: WriteTempScriptActionHandler(file_manager).handle,
    MultiEditAction: MultiEditActionHandler(file_manager).handle,
    FileMetadataAction: FileMetadataActionHandler(file_manager).handle,
    EditAction: EditActionHandler(file_manager).handle,
  }

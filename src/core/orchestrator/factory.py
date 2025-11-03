from pathlib import Path
from typing import Optional, Dict, Callable

from src.core.action import TaskCreateAction
from src.core.action.actions import LaunchSubagentAction, BatchTodoAction, AddNoteAction, ViewAllNotesAction, FinishAction, ReportAction, BashAction, GrepAction, GlobAction, LSAction, ReadAction, \
  WriteAction, WriteTempScriptAction, AddContextAction, MultiEditAction, FileMetadataAction, EditAction
from src.core.action.handlers import FinishActionHandler, ReportActionHandler
from src.core.agent import AgentManager, Subagent
from src.core.bash import CommandExecutor, DockerExecutor, FileManager, SearchManager
from src.core.bash.bash_handler import BashActionHandler
from src.core.bash.search_handlers import LSActionHandler, GlobActionHandler, GrepActionHandler
from src.core.context import ContextStore
from src.core.context.context_handler import AddContextActionHandler
from src.core.file.file_handlers import ReadActionHandler, WriteActionHandler, EditActionHandler, MultiEditActionHandler, FileMetadataActionHandler, WriteTempScriptActionHandler
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

orchestrator_model = "openai/gpt-5-2025-08-07"
subagent_model = "openai/gpt-5-mini-2025-08-07"


def create_orchestrator_agent(
    api_key: str,
    temperature: float,
    container_name: str,
    model: Optional[str] = None,
    command_executor: Optional[CommandExecutor] = None,
    logging_dir: Optional[Path] = None,
) -> OrchestratorAgent:
  """Factory function to create an OrchestratorAgent instance."""

  if command_executor is None:
    command_executor = DockerExecutor(container_name)

  task_store = TaskStore()
  todo_manager = TodoManager()
  scratchpad_manager = ScratchpadManager()
  context_store = ContextStore()
  file_manager = FileManager(command_executor)
  search_manager = SearchManager(command_executor)

  actions = get_sub_agent_actions(command_executor, context_store, file_manager, scratchpad_manager, search_manager, todo_manager)

  explorer_agent = Subagent(
      system_prompt=load_explorer_system_message(),
      actions=actions,
      agent_name="explorer",
      model=model or subagent_model,
      temperature=temperature,
      api_key=api_key,
      api_base=None,
      logging_dir=logging_dir,
  )

  coder_agent = Subagent(
      system_prompt=load_coder_system_message(),
      actions=actions,
      agent_name="coder",
      model=model or subagent_model,
      temperature=temperature,
      api_key=api_key,
      api_base=None,
      logging_dir=logging_dir,
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

  return OrchestratorAgent(
      system_prompt=load_orchestrator_system_message(),
      actions=orchestrator_action_handlers,
      task_manager=task_manager,
      task_store=task_store,
      context_store=context_store,
      model=model or orchestrator_model,
      temperature=temperature,
      logging_dir=logging_dir,
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

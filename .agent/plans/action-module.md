# Action Module Implementation

⚠️ Medium - Multiple files but straightforward from spec, may need iteration on validators

## Steps

- [x] **Step 1: Create `src/core/common/` utility module**
  - Create `src/core/common/__init__.py` exporting `format_tool_output`
  - Create `src/core/common/utils.py` with `format_tool_output(tool_name, content)` function
  - Validation: import and call `format_tool_output("test", "hello")` in Python

- [x] **Step 2: Create `src/core/action/actions.py` — all 20 action model classes**
  - `Action` base class (Pydantic BaseModel, extra=forbid, validate_assignment=True, to_dict())
  - Core: `BashAction`, `FinishAction`, `UserInputAction`
  - Todo: `TodoOperation` (BaseModel not Action), `BatchTodoAction`
  - File: `ReadAction`, `WriteAction`, `EditAction`, `EditOperation`, `MultiEditAction`, `FileMetadataAction`, `WriteTempScriptAction`
  - Search: `GrepAction`, `GlobAction`, `LSAction`
  - Scratchpad: `AddNoteAction`, `ViewAllNotesAction`
  - Task: `TaskCreateAction`, `AddContextAction`, `LaunchSubagentAction`, `ReportAction`
  - Validation: instantiate each model with valid data, confirm validation errors on invalid data

- [x] **Step 3: Create `src/core/action/actions_result.py` — ExecutionResult dataclass**
  - Dataclass with 6 fields (actions_executed, env_responses, has_error, finish_message, done, task_trajectories)
  - `to_dict()` method with conditional inclusion of task_trajectories
  - Validation: create instance and call to_dict()

- [x] **Step 4: Create `src/core/action/action_maps.py` — ACTION_MAP registry**
  - Dict mapping 19 XML tag strings to Action classes
  - Validation: confirm all 19 entries are present

- [x] **Step 5: Create `src/core/action/parser.py` — SimpleActionParser**
  - `IGNORED_TAGS` set: {'think', 'reasoning', 'plan_md'}
  - `_extract_xml_tags()` with exact regex pattern
  - `parse()` method with YAML parsing, ACTION_MAP lookup, model_validate
  - `parse_llm_output()` static convenience method
  - Validation: parse sample LLM output with valid/invalid/ignored tags

- [x] **Step 6: Create `src/core/action/handler_interface.py` — ActionHandlerInterface ABC**
  - Abstract `handle(action) -> Tuple[str, bool]`
  - Validation: confirm it's abstract and can't be instantiated

- [x] **Step 7: Create `src/core/action/action_handler.py` — ActionHandler class**
  - Constructor: `actions` dict + `agent_name`
  - `get_tools()`: parse + error formatting with block-scalar hint
  - `handle_tools()`: iterate actions, dispatch, break on FinishAction
  - `execute_tool_call()`: public method, handler lookup + unknown-action error
  - Validation: end-to-end test with mock handlers

- [x] **Step 8: Create `src/core/action/handlers/` — FinishActionHandler + ReportActionHandler**
  - `handlers/__init__.py` re-exporting both
  - `finish_handler.py`: returns formatted "Task marked as complete: {message}"
  - `report_handler.py`: returns formatted "Report submission successful"
  - Validation: call handle() on each and verify output format

- [x] **Step 9: Create `src/core/action/__init__.py` — public API surface**
  - Export exactly: Action, FinishAction, TaskCreateAction, ReportAction, SimpleActionParser, ActionHandlerInterface
  - `__all__` list with 6 symbols
  - Validation: import each symbol from `src.core.action`

- [x] **Step 10: Run full validation**
  - Write and run a test script that exercises parsing, dispatching, and result collection
  - Confirm all imports resolve, all validators work, all handlers produce correct output

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Action(BaseModel):
    model_config = {"extra": "forbid", "validate_assignment": True}

    def to_dict(self) -> dict:
        return self.model_dump()


# --- Core Actions ---

class BashAction(Action):
    cmd: str = Field(min_length=1)
    block: bool = True
    timeout_secs: int = Field(default=30, gt=0, le=300)


class FinishAction(Action):
    message: str = "Task completed"


class UserInputAction(Action):
    prompt: str = Field(min_length=1)
    options: List[str] = []
    allow_empty: bool = False
    timeout_secs: int = Field(default=60, gt=0, le=300)


# --- Todo Actions ---

class TodoOperation(BaseModel):
    model_config = {"extra": "forbid", "validate_assignment": True}

    action: Literal["add", "complete", "delete", "view_all"]
    content: Optional[str] = None
    task_id: Optional[int] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("action") == "add" and not v:
            raise ValueError("content is required for 'add' action")
        return v

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: Optional[int], info) -> Optional[int]:
        action = info.data.get("action")
        if action in ("complete", "delete"):
            if v is None or v <= 0:
                raise ValueError(f"task_id must be a positive int for '{action}' action")
        return v

    @model_validator(mode="after")
    def validate_operation(self) -> "TodoOperation":
        if self.action == "add" and not self.content:
            raise ValueError("content is required for 'add' action")
        if self.action in ("complete", "delete"):
            if self.task_id is None or self.task_id <= 0:
                raise ValueError(f"task_id must be a positive int for '{self.action}' action")
        return self


class BatchTodoAction(Action):
    operations: List[TodoOperation] = Field(min_length=1)
    view_all: bool = False


# --- File Actions ---

class ReadAction(Action):
    file_path: str = Field(min_length=1)
    offset: Optional[int] = Field(default=None, ge=0)
    limit: Optional[int] = Field(default=None, gt=0)


class WriteAction(Action):
    file_path: str = Field(min_length=1)
    content: str


class EditAction(Action):
    file_path: str = Field(min_length=1)
    old_string: str
    new_string: str
    replace_all: bool = False


class EditOperation(BaseModel):
    model_config = {"extra": "forbid", "validate_assignment": True}

    old_string: str
    new_string: str
    replace_all: bool = False


class MultiEditAction(Action):
    file_path: str = Field(min_length=1)
    edits: List[EditOperation] = Field(min_length=1)


class FileMetadataAction(Action):
    file_paths: List[str] = Field(min_length=1, max_length=10)


class WriteTempScriptAction(Action):
    file_path: str = Field(min_length=1)
    content: str


# --- Search Actions ---

class GrepAction(Action):
    pattern: str = Field(min_length=1)
    path: Optional[str] = None
    include: Optional[str] = None


class GlobAction(Action):
    pattern: str = Field(min_length=1)
    path: Optional[str] = None


class LSAction(Action):
    path: str = Field(min_length=1)
    ignore: List[str] = []


# --- Scratchpad Actions ---

class AddNoteAction(Action):
    content: str = Field(min_length=1)


class ViewAllNotesAction(Action):
    pass


# --- Task Management Actions ---

class TaskCreateAction(Action):
    agent_name: Literal["explorer", "coder"]
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    context_refs: List[str] = []
    context_bootstrap: List[dict] = []
    auto_launch: bool = False

    @field_validator("context_bootstrap")
    @classmethod
    def validate_context_bootstrap(cls, v: List[dict]) -> List[dict]:
        for item in v:
            if not isinstance(item, dict) or "path" not in item or "reason" not in item:
                raise ValueError("Each context_bootstrap item must be a dict with 'path' and 'reason' keys")
        return v


class AddContextAction(Action):
    id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    reported_by: str = "?"
    task_id: Optional[str] = None


class LaunchSubagentAction(Action):
    task_id: str = Field(min_length=1)


class ReportAction(Action):
    contexts: List[dict] = []
    comments: str = ""

"""Simplified action parser using Pydantic models for validation."""

import logging
import re
from typing import List, Tuple, Type, Optional

import yaml

from src.core.action.action_maps import ACTION_MAP, FILE_ACTIONS, SEARCH_ACTIONS
from src.core.action.actions import (
    Action,
    AddNoteAction, ViewAllNotesAction,
)


class SimpleActionParser:
  """Clean parser that delegates validation to Pydantic models."""


  # Tags to ignore (not actions)
  IGNORED_TAGS = {'think', 'reasoning', 'plan_md'}

  def __init__(self):
    self.logger = logging.getLogger(__name__)

  @staticmethod
  def parse_llm_output(llm_output: str) -> Tuple[List[Action], List[str], bool]:
    """Parse LLM output into actions.

    Returns:
        Tuple of (actions, errors, found_action_attempt)
    """
    action_parser = SimpleActionParser()
    return action_parser.parse(llm_output)

  def parse(self, response: str) -> Tuple[List[Action], List[str], bool]:
    """Parse agent response into actions.

    Returns:
        Tuple of (actions, errors, found_action_attempt)
    """
    actions = []
    errors = []
    found_action_attempt = False

    # Extract XML tags
    for tag_name, content in self._extract_xml_tags(response):
      # Skip non-action tags
      if tag_name.lower() in self.IGNORED_TAGS:
        self.logger.debug(f"Skipping {tag_name} tag (not an action)")
        continue

      found_action_attempt = True

      try:
        data = yaml.safe_load(content.strip())
        action_class, cleaned_data = self._get_action_class_and_data(tag_name, data)
        if not action_class:
          errors.append(f"Unknown action type: {tag_name}")
          continue

        # Let Pydantic validate and create the action
        action = action_class.model_validate(cleaned_data)
        actions.append(action)

      except yaml.YAMLError as e:
        errors.append(f"[{tag_name}] YAML error: {e}")
      except ValueError as e:
        # Pydantic validation errors are more descriptive
        errors.append(f"[{tag_name}] Validation error: {e}")
      except Exception as e:
        errors.append(f"[{tag_name}] Unexpected error: {e}")

    return actions, errors, found_action_attempt

  @staticmethod
  def _extract_xml_tags(response: str) -> List[Tuple[str, str]]:
    """Extract XML tag pairs from response."""
    # Match top-level tags (not nested)
    pattern = r'(?:^|\n)\s*<(\w+)>([\s\S]*?)</\1>'
    matches = re.findall(pattern, response, re.MULTILINE)
    return matches

  def _get_action_class_and_data(self, tag_name: str, data: dict) -> Tuple[Optional[Type[Action]], dict]:
    """Get the appropriate Action class and cleaned data for a tag.

    Returns:
        Tuple of (action_class, cleaned_data)
    """

    # Direct mapping - no data cleaning needed
    if tag_name in ACTION_MAP and ACTION_MAP[tag_name]:
      return ACTION_MAP[tag_name], data

    # Special handling for multi-action tags that use 'action' field
    if tag_name == 'file':
      action_type = data.get('action') if isinstance(data, dict) else None
      action_class = FILE_ACTIONS.get(action_type)
      if action_class and isinstance(data, dict):
        # Remove 'action' field since Pydantic models don't expect it
        cleaned_data = {k: v for k, v in data.items() if k != 'action'}
        return action_class, cleaned_data
      return None, data

    elif tag_name == 'search':
      action_type = data.get('action') if isinstance(data, dict) else None
      action_class = SEARCH_ACTIONS.get(action_type)
      if action_class and isinstance(data, dict):
        # Remove 'action' field
        cleaned_data = {k: v for k, v in data.items() if k != 'action'}
        return action_class, cleaned_data
      return None, data

    elif tag_name == 'scratchpad':
      action_type = data.get('action') if isinstance(data, dict) else None
      if action_type == 'add_note':
        # Only keep 'content' field
        cleaned_data = {'content': data.get('content', '')}
        return AddNoteAction, cleaned_data
      elif action_type == 'view_all_notes':
        return ViewAllNotesAction, {}
      return None, data

    return None, data


# Example usage
if __name__ == "__main__":
  parser = SimpleActionParser()

  # Test various action formats
  test_response = """
<bash>
cmd: "ls -la"
timeout_secs: 45
</bash>

<file>
action: read
file_path: "/tmp/test.txt"
limit: 100
</file>

<todo>
operations:
  - action: add
    content: "Implement new feature"
  - action: complete
    task_id: 1
</todo>

<finish>
message: "Task completed successfully"
</finish>
"""

  actions, errors, found = parser.parse(test_response)

  print(f"Found action attempt: {found}")
  print(f"Parsed {len(actions)} actions:")
  for action in actions:
    print(f"  - {action.__class__.__name__}: {action}")

  if errors:
    print(f"Errors: {errors}")

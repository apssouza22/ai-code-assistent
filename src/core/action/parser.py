"""Simplified action parser using Pydantic models for validation."""

import logging
import re
from typing import List, Tuple, Type, Optional

import yaml

from src.core.action.action_maps import ACTION_MAP
from src.core.action.actions import Action


class SimpleActionParser:
  """Clean parser that delegates validation to Pydantic models."""

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

    for tag_name, content in self._extract_xml_tags(response):
      if tag_name.lower() in self.IGNORED_TAGS:
        self.logger.debug(f"Skipping {tag_name} tag (not an action)")
        continue

      found_action_attempt = True

      try:
        data = yaml.safe_load(content.strip())
        action_class = ACTION_MAP.get(tag_name)
        if not action_class:
          errors.append(f"Unknown action type: {tag_name}")
          continue

        if data is None:
          data = {}

        action = action_class.model_validate(data)
        actions.append(action)

      except yaml.YAMLError as e:
        errors.append(f"[{tag_name}] YAML error: {e}")
      except ValueError as e:
        errors.append(f"[{tag_name}] Validation error: {e}")
      except Exception as e:
        errors.append(f"[{tag_name}] Unexpected error: {e}")

    return actions, errors, found_action_attempt

  @staticmethod
  def _extract_xml_tags(response: str) -> List[Tuple[str, str]]:
    """Extract XML tag pairs from response."""
    pattern = r'(?:^|\n)\s*<(\w+)>([\s\S]*?)</\1>'
    matches = re.findall(pattern, response, re.MULTILINE)
    return matches


# Example usage
if __name__ == "__main__":
  parser = SimpleActionParser()

  test_response = """
<bash>
cmd: "ls -la"
timeout_secs: 45
</bash>

<read_file>
file_path: "/tmp/test.txt"
limit: 100
</read_file>

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

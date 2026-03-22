import logging
import re
from typing import List, Tuple

import yaml

from src.core.action.action_maps import ACTION_MAP
from src.core.action.actions import Action

logger = logging.getLogger(__name__)

IGNORED_TAGS = {"think", "reasoning", "plan_md"}


class SimpleActionParser:

    @staticmethod
    def parse_llm_output(llm_output: str) -> Tuple[List[Action], List[str], bool]:
        parser = SimpleActionParser()
        return parser.parse(llm_output)

    def parse(self, response: str) -> Tuple[List[Action], List[str], bool]:
        actions: List[Action] = []
        errors: List[str] = []
        found_action_attempt = False

        xml_tags = self._extract_xml_tags(response)

        for tag_name, content in xml_tags:
            if tag_name.lower() in IGNORED_TAGS:
                continue

            found_action_attempt = True

            try:
                data = yaml.safe_load(content.strip())
            except yaml.YAMLError as e:
                errors.append(f"YAML parse error in <{tag_name}>: {e}")
                continue

            action_class = ACTION_MAP.get(tag_name)
            if action_class is None:
                errors.append(f"Unknown action type: {tag_name}")
                continue

            if data is None:
                data = {}

            try:
                action = action_class.model_validate(data)
                actions.append(action)
            except ValueError as e:
                errors.append(f"Validation error in <{tag_name}>: {e}")
            except Exception as e:
                errors.append(f"Error parsing <{tag_name}>: {e}")

        return actions, errors, found_action_attempt

    @staticmethod
    def _extract_xml_tags(response: str) -> List[Tuple[str, str]]:
        pattern = r'(?:^|\n)\s*<(\w+)>([\s\S]*?)</\1>'
        return re.findall(pattern, response, re.MULTILINE)

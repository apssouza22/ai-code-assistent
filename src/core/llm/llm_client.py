"""Centralized LLM client for making LiteLLM calls."""

import os
import copy
import time
import random
import logging
import threading
from typing import List, Dict, Optional, Any

import litellm
from litellm.exceptions import InternalServerError
from litellm.utils import token_counter

from src.core.llm.llm_config import LlmConfig
from src.misc import pretty_log


def _apply_anthropic_caching_if_possible(messages: List[Dict[str, Any]], model: str) -> List[Dict[str, Any]]:
    """Apply prompt caching for Anthropic models.

    Args:
        messages: List of message dictionaries
        model: Model name

    Returns:
        Messages with cache_control applied for Anthropic models
    """
    # Only apply caching for Anthropic models
    if not (model and "anthropic/" in model):
        return messages

    # Deep copy messages to avoid modifying the original
    cached_messages = copy.deepcopy(messages)

    # Find indices of system and user messages
    system_idx = None
    user_indices = []

    for i, msg in enumerate(cached_messages):
        if msg.get("role") == "system":
            system_idx = i
        elif msg.get("role") == "user":
            user_indices.append(i)

    # Apply cache control to system message
    if system_idx is not None:
        msg = cached_messages[system_idx]
        # Convert content to the format required for caching
        if isinstance(msg.get("content"), str):
            msg["content"] = [
                {
                    "type": "text",
                    "text": msg["content"],
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        elif isinstance(msg.get("content"), list):
            # Add cache_control to existing content items
            for item in msg["content"]:
                if isinstance(item, dict) and "text" in item:
                    item["cache_control"] = {"type": "ephemeral"}

    # Apply cache control to last 2 user messages
    if len(user_indices) >= 1:
        # Cache the last user message
        last_user_idx = user_indices[-1]
        msg = cached_messages[last_user_idx]
        if isinstance(msg.get("content"), str):
            msg["content"] = [
                {
                    "type": "text",
                    "text": msg["content"],
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        elif isinstance(msg.get("content"), list):
            for item in msg["content"]:
                if isinstance(item, dict) and "text" in item:
                    item["cache_control"] = {"type": "ephemeral"}

    if len(user_indices) >= 2:
        # Cache the second-to-last user message
        second_last_user_idx = user_indices[-2]
        msg = cached_messages[second_last_user_idx]
        if isinstance(msg.get("content"), str):
            msg["content"] = [
                {
                    "type": "text",
                    "text": msg["content"],
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        elif isinstance(msg.get("content"), list):
            for item in msg["content"]:
                if isinstance(item, dict) and "text" in item:
                    item["cache_control"] = {"type": "ephemeral"}

    return cached_messages


def get_llm_response(
    messages: List[Dict[str, Any]],
    llm_config: LlmConfig,
    api_base: Optional[str] = None,
    max_retries: int = 10
) -> str:
    start = time.time()
    model = llm_config.model
    temperature = llm_config.temperature
    max_tokens = llm_config.max_tokens

    if llm_config.api_key or (api_key := os.getenv("LITE_LLM_API_KEY")):
        litellm.api_key = llm_config.api_key or api_key
    if api_base or (api_base := os.getenv("LITE_LLM_API_BASE")):
        litellm.api_base = api_base

    processed_messages = _apply_anthropic_caching_if_possible(messages, model)

    for attempt in range(max_retries):
        try:
            is_reasoning_model = "gpt-5" in model
            token_params = {"max_completion_tokens": max_tokens} if is_reasoning_model else {"max_tokens": max_tokens}
            response = litellm.completion(
                model=model,
                messages=processed_messages,
                temperature=temperature,
                reasoning_effort="low" if is_reasoning_model else None,
                **token_params
            )
            return response.choices[0].message.content # type: ignore

        except InternalServerError as e:
            if "overloaded_error" in str(e):
                if attempt < max_retries - 1:
                    base_delay = 2 ** attempt
                    jitter = random.uniform(0, base_delay * 0.1)
                    delay = min(base_delay + jitter, 60)

                    pretty_log.warning(f"Anthropic overloaded, retrying in {delay:.2f} seconds (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    raise
            else:
                raise

        except Exception:
            raise

    raise RuntimeError("Failed to get LLM response after maximum retries.")


def _try_token_counter_with_timeout(model: str, messages: List[Dict[str, Any]],
                                     timeout: float = 2.0) -> Optional[int]:
    """Try to count tokens with a timeout.

    Args:
        model: Model name for token counting
        messages: List of message dictionaries
        timeout: Timeout in seconds

    Returns:
        Token count if successful, None if failed or timed out
    """
    result = [None]
    exception = [None]

    def run_token_counter():
        try:
            result[0] = token_counter(model=model, messages=messages)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=run_token_counter)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        # Thread is still running, timeout occurred
        logging.warning(
            f"Token counting timed out for model {model} after {timeout}s"
        )
        return None
    elif exception[0]:
        logging.warning(
            f"Failed to count tokens with model {model}: {exception[0]}"
        )
        return None
    else:
        return result[0]


def count_tokens_for_messages(messages: List[Dict[str, Any]], model: Optional[str] = None) -> int:
    """Count total tokens in a list of messages.

    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model: Model name for accurate token counting (defaults to gpt-3.5-turbo)

    Returns:
        Total token count for all messages
    """
    if not messages:
        return 0

    model = model or os.getenv("LITELLM_MODEL", "gpt-5")

    # Try with the specified model first
    token_count = _try_token_counter_with_timeout(model, messages)
    if token_count is not None:
        return token_count

    # Try with openai/gpt-5 as fallback
    logging.info("Retrying token counting with openai/gpt-5")
    token_count = _try_token_counter_with_timeout("openai/gpt-5", messages)
    if token_count is not None:
        return token_count

    # Final fallback: estimate ~4 chars per token
    logging.warning("Using character-based token estimation")
    total_chars = sum(len(str(msg.get("content", ""))) for msg in messages)
    return total_chars // 4


def count_input_tokens(messages: List[Dict[str, Any]], model: Optional[str] = None) -> int:
    """Count tokens for input messages (system and user roles).

    Args:
        messages: List of message dictionaries
        model: Model name for accurate token counting

    Returns:
        Token count for system and user messages
    """
    input_messages = [
        msg for msg in messages
        if msg.get("role") in ["system", "user"]
    ]
    return count_tokens_for_messages(input_messages, model)


def count_output_tokens(messages: List[Dict[str, Any]], model: Optional[str] = None) -> int:
    """Count tokens for output messages (assistant role).

    Args:
        messages: List of message dictionaries
        model: Model name for accurate token counting

    Returns:
        Token count for assistant messages
    """
    output_messages = [
        msg for msg in messages
        if msg.get("role") == "assistant"
    ]
    return count_tokens_for_messages(output_messages, model)

"""JSON parsing utilities for LLM responses.

This module provides utilities for parsing JSON responses from LLM models,
handling common edge cases like markdown code blocks and extra whitespace.

Based on proven pattern from llm_fallback.py:348-383.
"""

import json
from typing import Any, Dict, List, Union, Optional

from .logger import get_logger

logger = get_logger(__name__)


def parse_llm_json_response(
    response_text: str,
    expected_type: type = dict,
    fallback_value: Optional[Any] = None
) -> Any:
    """Parse LLM JSON response with markdown unwrapping.

    Handles common LLM output formats:
    - Plain JSON: `{"key": "value"}`
    - Markdown-wrapped JSON: ```json\n{"key": "value"}\n```
    - Markdown-wrapped without tag: ```\n{"key": "value"}\n```
    - Extra whitespace and newlines

    Args:
        response_text: Raw text response from LLM (potentially markdown-wrapped)
        expected_type: Expected Python type (dict, list, etc.)
        fallback_value: Value to return on parse failure. If None, raises ValueError.

    Returns:
        Parsed JSON data as the expected type

    Raises:
        ValueError: If JSON parsing fails and fallback_value is None

    Examples:
        >>> parse_llm_json_response('{"key": "value"}', expected_type=dict)
        {'key': 'value'}

        >>> parse_llm_json_response('```json\\n{"key": "value"}\\n```', expected_type=dict)
        {'key': 'value'}

        >>> parse_llm_json_response('invalid', expected_type=dict, fallback_value={})
        {}
    """
    if not isinstance(response_text, str):
        logger.warning(
            "Invalid response_text type",
            response_type=type(response_text).__name__,
            expected_type="str"
        )
        if fallback_value is None:
            raise ValueError(f"response_text must be string, got {type(response_text)}")
        return fallback_value

    # Remove markdown code blocks if present
    cleaned_text = response_text.strip()

    if cleaned_text.startswith("```"):
        # Extract content between ``` markers
        # Find the opening and closing braces/brackets for JSON
        start = cleaned_text.find("{")
        end = cleaned_text.rfind("}") + 1

        # Also check for JSON arrays
        if start < 0 or start > 10:  # { should be near the start after ```
            start = cleaned_text.find("[")
            end = cleaned_text.rfind("]") + 1

        if start >= 0 and end > start:
            cleaned_text = cleaned_text[start:end]
        else:
            logger.warning(
                "Markdown wrapper detected but no JSON found",
                response_preview=response_text[:100]
            )
            if fallback_value is None:
                raise ValueError("No JSON content found in markdown wrapper")
            return fallback_value

    # Try to parse JSON
    try:
        data = json.loads(cleaned_text.strip())

        # Validate type
        if not isinstance(data, expected_type):
            logger.warning(
                "Parsed JSON has unexpected type",
                expected_type=expected_type.__name__,
                actual_type=type(data).__name__
            )
            if fallback_value is None:
                raise ValueError(f"Expected {expected_type}, got {type(data)}")
            return fallback_value

        logger.debug(
            "Successfully parsed LLM JSON response",
            response_length=len(response_text),
            parsed_type=type(data).__name__
        )
        return data

    except json.JSONDecodeError as e:
        logger.warning(
            "Failed to parse JSON response",
            error=str(e),
            response_preview=cleaned_text[:200]
        )
        if fallback_value is None:
            raise ValueError(f"Invalid JSON in response: {str(e)}")
        return fallback_value


def parse_agent_json_output(
    output: Any,
    field_name: str = "output",
    fallback_value: Optional[Dict] = None
) -> Dict:
    """Parse agent output which may be a dict or JSON string.

    Convenience wrapper around parse_llm_json_response() for agent outputs.

    Args:
        output: Agent output (dict, string, or other)
        field_name: Name of the field (for logging)
        fallback_value: Fallback value if parsing fails (default: {})

    Returns:
        Parsed dictionary

    Examples:
        >>> parse_agent_json_output({"key": "value"})
        {'key': 'value'}

        >>> parse_agent_json_output('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}
    """
    if fallback_value is None:
        fallback_value = {}

    # Already a dict - passthrough
    if isinstance(output, dict):
        logger.debug(
            "Agent output already dict",
            field_name=field_name,
            keys=list(output.keys())
        )
        return output

    # String - try to parse
    if isinstance(output, str):
        logger.debug(
            "Parsing agent string output",
            field_name=field_name,
            length=len(output)
        )
        return parse_llm_json_response(
            output,
            expected_type=dict,
            fallback_value=fallback_value
        )

    # Other type - log warning and return fallback
    logger.warning(
        "Unexpected agent output type",
        field_name=field_name,
        output_type=type(output).__name__
    )
    return fallback_value

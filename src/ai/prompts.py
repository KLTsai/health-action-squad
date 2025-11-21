"""Prompt management utilities for Health Action Squad.

Handles loading and managing agent system prompts from external files.
"""

from pathlib import Path
from typing import Optional


def load_prompt(prompt_name: str, base_path: Optional[Path] = None) -> str:
    """Load agent system prompt from file.

    Args:
        prompt_name: Name of the prompt file (without extension)
        base_path: Base path for prompts directory (defaults to resources/prompts/)

    Returns:
        Prompt content as string

    Raises:
        FileNotFoundError: If prompt file doesn't exist

    Example:
        >>> prompt = load_prompt("analyst_prompt")
        >>> # Loads from resources/prompts/analyst_prompt.txt
    """
    if base_path is None:
        # Get project root (4 levels up from this file: ai -> src -> project root)
        project_root = Path(__file__).parent.parent.parent
        base_path = project_root / "resources" / "prompts"

    prompt_file = base_path / f"{prompt_name}.txt"

    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_file}\n"
            f"Available prompts should be in: {base_path}"
        )

    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()


def get_prompt_path(prompt_name: str, base_path: Optional[Path] = None) -> Path:
    """Get the full path to a prompt file.

    Args:
        prompt_name: Name of the prompt file (without extension)
        base_path: Base path for prompts directory

    Returns:
        Path object for the prompt file
    """
    if base_path is None:
        project_root = Path(__file__).parent.parent.parent
        base_path = project_root / "resources" / "prompts"

    return base_path / f"{prompt_name}.txt"


def list_available_prompts(base_path: Optional[Path] = None) -> list[str]:
    """List all available prompt files.

    Args:
        base_path: Base path for prompts directory

    Returns:
        List of prompt names (without .txt extension)
    """
    if base_path is None:
        project_root = Path(__file__).parent.parent.parent
        base_path = project_root / "resources" / "prompts"

    if not base_path.exists():
        return []

    return [p.stem for p in base_path.glob("*.txt")]

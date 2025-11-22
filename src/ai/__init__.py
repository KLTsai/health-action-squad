"""AI module for Health Action Squad.

Contains LLM client abstractions, tools, and prompt management.
"""

from .client import AIClientFactory
from .prompts import load_prompt, get_prompt_path, list_available_prompts
# from .tools import MedicalKnowledgeSearchTool  # Not yet implemented

__all__ = [
    "AIClientFactory",
    "load_prompt",
    "get_prompt_path",
    "list_available_prompts",
    # "MedicalKnowledgeSearchTool",  # Not yet implemented
]

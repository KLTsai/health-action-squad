"""AI Client factory for Health Action Squad.

Provides centralized ModelClient management for all agents.
"""

from typing import Optional
import os
import google.generativeai as genai
from google.generativeai import GenerativeModel


class AIClientFactory:
    """Factory for creating and managing AI model clients.

    Centralizes LLM client configuration and provides easy model switching.
    """

    @staticmethod
    def create_gemini_client(
        api_key: Optional[str] = None,
        model: str = "gemini-pro",
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
    ) -> GenerativeModel:
        """Create a Gemini GenerativeModel client.

        Args:
            api_key: Gemini API key (falls back to env var GEMINI_API_KEY)
            model: Model name (default: gemini-pro)
            temperature: Sampling temperature (default: 0.7)
            max_output_tokens: Maximum tokens in response (default: 2048)

        Returns:
            Configured GenerativeModel instance

        Raises:
            ValueError: If API key is not provided
        """
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment")

        # Configure Gemini API
        genai.configure(api_key=api_key)

        # Create generation config
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        # Create and return model
        model_instance = GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )

        return model_instance

    @staticmethod
    def create_default_client() -> GenerativeModel:
        """Create default client using config settings.

        Returns:
            Default configured GenerativeModel
        """
        from ..common.config import Config

        return AIClientFactory.create_gemini_client(
            api_key=Config.GEMINI_API_KEY,
            model=Config.MODEL_NAME,
            temperature=Config.TEMPERATURE,
            max_output_tokens=Config.MAX_TOKENS,
        )

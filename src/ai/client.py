"""AI Client factory for Health Action Squad.

Provides centralized ModelClient management for all agents.
"""

from typing import Optional
import os


class AIClientFactory:
    """Factory for creating and managing AI model clients.

    Centralizes LLM client configuration and provides easy model switching.
    """

    @staticmethod
    def create_gemini_client(
        api_key: Optional[str] = None,
        model: str = "gemini-pro",
        temperature: float = 0.7,
    ):
        """Create a Gemini ModelClient.

        Args:
            api_key: Gemini API key (falls back to env var GEMINI_API_KEY)
            model: Model name (default: gemini-pro)
            temperature: Sampling temperature (default: 0.7)

        Returns:
            Configured ModelClient instance

        Raises:
            ValueError: If API key is not provided
        """
        # TODO: Implement when Google ADK is installed
        # from google.adk.clients import ModelClient

        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment")

        # Placeholder - will be implemented with ADK
        # return ModelClient(
        #     model=model,
        #     api_key=api_key,
        #     temperature=temperature
        # )

        raise NotImplementedError("ADK ModelClient integration pending")

    @staticmethod
    def create_default_client():
        """Create default client using config settings.

        Returns:
            Default configured ModelClient
        """
        from ..common.config import Config

        config = Config()
        return AIClientFactory.create_gemini_client(
            api_key=config.GEMINI_API_KEY,
            model=config.MODEL_NAME,
            temperature=config.TEMPERATURE,
        )

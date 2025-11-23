"""Configuration management for Health Action Squad.

Loads configuration from environment variables and provides
centralized access to all settings.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration.

    All configuration values should be accessed through this class.
    Environment variables take precedence over defaults.
    """

    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    SRC_DIR = PROJECT_ROOT / "src"
    RESOURCES_DIR = PROJECT_ROOT / "resources"
    PROMPTS_DIR = RESOURCES_DIR / "prompts"
    POLICIES_DIR = RESOURCES_DIR / "policies"
    DATA_DIR = RESOURCES_DIR / "data"
    OUTPUT_DIR = PROJECT_ROOT / "output"
    LOGS_DIR = PROJECT_ROOT / "logs"

    # API Keys
    # Note: GOOGLE_API_KEY is kept for backwards compatibility but not currently used
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Model configuration
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2048"))

    # Workflow configuration
    # Note: MAX_RETRIES is defined here but currently src/domain/state.py uses a hardcoded value
    # This may be used in future for dynamic configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # API server configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "1"))

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
    RATE_LIMIT_PERIOD: str = os.getenv("RATE_LIMIT_PERIOD", "1 hour")

    # File upload configuration
    MAX_UPLOAD_FILES: int = int(os.getenv("MAX_UPLOAD_FILES", "10"))
    MAX_TOTAL_UPLOAD_SIZE: int = int(
        os.getenv("MAX_TOTAL_UPLOAD_SIZE", str(50 * 1024 * 1024))
    )  # 50MB default
    MAX_FILE_SIZE: int = int(
        os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024))
    )  # 10MB per file

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    # Safety policy
    SAFETY_RULES_PATH: Path = POLICIES_DIR / "safety_rules.yaml"

    # Prompts
    ANALYST_PROMPT_PATH: Path = PROMPTS_DIR / "analyst_prompt.txt"
    PLANNER_PROMPT_PATH: Path = PROMPTS_DIR / "planner_prompt.txt"
    GUARD_PROMPT_PATH: Path = PROMPTS_DIR / "guard_prompt.txt"

    @classmethod
    def validate(cls) -> None:
        """Validate configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if not cls.GOOGLE_API_KEY and not cls.GEMINI_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY or GEMINI_API_KEY must be set in environment variables"
            )

        # Ensure required directories exist
        for directory in [cls.OUTPUT_DIR, cls.LOGS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_prompt(cls, prompt_path: Path) -> str:
        """Load prompt from file.

        Args:
            prompt_path: Path to prompt file

        Returns:
            Prompt text

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        return prompt_path.read_text(encoding="utf-8")


# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    import sys

    # Use ASCII for compatibility
    sys.stderr.write(f"Configuration warning: {e}\n")
    sys.stderr.write("Please set up your .env file with required API keys\n")

"""LifestylePlannerAgent - Lifestyle plan generation agent.

Generates personalized lifestyle plans using Google ADK.

State Injection:
- Uses InstructionProvider with inject_session_state for reliable state injection
  - {health_analysis} - From ReportAnalyst output
  - {user_profile} - From initial state
  - {validation_result} - From SafetyGuard feedback on retry

Logging:
- Agent creation is logged in orchestrator during workflow initialization
- Execution tracing with iteration number is handled by orchestrator.execute()
"""

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models import Gemini
from google.genai.types import GenerateContentConfig
from google.adk.utils.instructions_utils import inject_session_state

from ..ai import load_prompt
from ..common.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LifestylePlannerAgent:
    """Factory for creating LifestylePlanner ADK agent.

    Responsibilities:
    - Combine health_metrics, risk_tags, and user_profile
    - Generate Markdown lifestyle plan (max 1500 words)
    - Medical recommendations MUST cite sources
    - Incorporate Guard feedback in retry loop

    System prompt loaded from: resources/prompts/planner_prompt.txt
    """

    @staticmethod
    async def _build_planner_instruction(readonly_context: ReadonlyContext) -> str:
        """InstructionProvider: Dynamically build Planner instruction with session state injection.

        Args:
            readonly_context: ADK readonly context with session state access

        Returns:
            Fully populated instruction string
        """
        prompt_template = load_prompt("planner_prompt")
        return await inject_session_state(prompt_template, readonly_context)

    @staticmethod
    def create_agent(model_name: str = "gemini-2.5-flash") -> LlmAgent:
        """Create ADK LlmAgent for lifestyle plan generation with InstructionProvider.

        Args:
            model_name: Gemini model name (default: gemini-2.5-flash)

        Returns:
            Configured LlmAgent instance with InstructionProvider
        """
        # Create ADK Gemini model instance
        gemini_model = Gemini(model=model_name)

        # Create generation config with temperature and max_tokens from Config
        gen_config = GenerateContentConfig(
            temperature=Config.TEMPERATURE,
            max_output_tokens=Config.MAX_TOKENS
        )

        logger.info(
            "LifestylePlanner agent created with InstructionProvider",
            model=model_name,
            temperature=Config.TEMPERATURE,
            max_output_tokens=Config.MAX_TOKENS,
            output_key="current_plan",
            description="Generates personalized lifestyle plans from health metrics",
            instruction_provider="LifestylePlannerAgent._build_planner_instruction"
        )

        # ADK LlmAgent with InstructionProvider
        return LlmAgent(
            name="LifestylePlanner",
            model=gemini_model,
            instruction=LifestylePlannerAgent._build_planner_instruction,
            generate_content_config=gen_config,
            output_key="current_plan",
            description="Generates personalized lifestyle plans from health metrics"
        )

"""ReportAnalystAgent - Health report parsing agent.

Parses health reports into structured metrics and risk tags using Google ADK.

State Injection:
- Uses InstructionProvider with inject_session_state for reliable state injection
  - {health_report} - From initial state

Logging:
- Agent creation is logged in orchestrator during workflow initialization
- Execution tracing is handled by orchestrator.execute()
"""

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models import Gemini
from google.genai.types import GenerateContentConfig

from ..ai import load_prompt
from ..common.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ReportAnalystAgent:
    """Factory for creating ReportAnalyst ADK agent.

    Responsibilities:
    - Parse raw health report data
    - Extract health metrics (cholesterol, blood pressure, etc.)
    - Identify risk tags based on report findings
    - NO external queries allowed
    - Output MUST conform to SessionState schema

    System prompt loaded from: resources/prompts/analyst_prompt.txt
    """

    @staticmethod
    async def _build_analyst_instruction(readonly_context: ReadonlyContext) -> str:
        """InstructionProvider: Dynamically build Analyst instruction with session state injection.

        Note: health_report data is passed via user message in RunnerExecutor.
        This method prepares the system prompt with JSON-serialized state values.

        Args:
            readonly_context: ADK readonly context with session state access

        Returns:
            Fully populated instruction string with state placeholders replaced
        """
        import json
        from google.adk.utils.instructions_utils import inject_session_state

        prompt_template = load_prompt("analyst_prompt")

        # Pre-process state: Convert dict values to JSON strings
        # ADK inject_session_state expects string values, not dict objects
        state = readonly_context.session.state
        modified_state = dict(state)

        if "health_report" in modified_state and isinstance(modified_state["health_report"], dict):
            modified_state["health_report"] = json.dumps(modified_state["health_report"], indent=2)

        # Temporarily update state with JSON-serialized values
        original_state = dict(state)
        try:
            state.update(modified_state)
            return await inject_session_state(prompt_template, readonly_context)
        finally:
            # Restore original state to avoid side effects
            state.clear()
            state.update(original_state)

    @staticmethod
    def create_agent(model_name: str = "gemini-2.5-flash") -> LlmAgent:
        """Create ADK LlmAgent for report analysis with InstructionProvider.

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
            "ReportAnalyst agent created with InstructionProvider",
            model=model_name,
            temperature=Config.TEMPERATURE,
            max_output_tokens=Config.MAX_TOKENS,
            output_key="health_analysis",
            description="Parses health reports into structured metrics and risk tags",
            instruction_provider="ReportAnalystAgent._build_analyst_instruction"
        )

        # ADK LlmAgent with InstructionProvider
        return LlmAgent(
            name="ReportAnalyst",
            model=gemini_model,
            instruction=ReportAnalystAgent._build_analyst_instruction,
            generate_content_config=gen_config,
            output_key="health_analysis",
            description="Parses health reports into structured metrics and risk tags"
        )

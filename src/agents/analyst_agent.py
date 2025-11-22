"""ReportAnalystAgent - Health report parsing agent.

Parses health reports into structured metrics and risk tags using Google ADK.

Logging:
- Agent creation is logged in orchestrator during workflow initialization
- Execution tracing is handled by orchestrator.execute()
"""

from google.adk.agents import LlmAgent

from ..ai import load_prompt
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
    def create_agent(model_name: str = "gemini-2.5-flash") -> LlmAgent:
        """Create ADK LlmAgent for report analysis.

        Args:
            model_name: Gemini model name (default: gemini-2.5-flash)

        Returns:
            Configured LlmAgent instance
        """
        # Load system prompt from external file
        system_prompt = load_prompt("analyst_prompt")

        logger.info(
            "ReportAnalyst agent created",
            model=model_name,
            output_key="health_analysis",
            description="Parses health reports into structured metrics and risk tags"
        )

        return LlmAgent(
            name="ReportAnalyst",
            model=model_name,
            instruction=system_prompt,
            output_key="health_analysis",
            description="Parses health reports into structured metrics and risk tags"
        )

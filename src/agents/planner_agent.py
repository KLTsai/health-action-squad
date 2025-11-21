"""LifestylePlannerAgent - Lifestyle plan generation agent.

Generates personalized lifestyle plans using Google ADK.

State Injection:
- Uses ADK placeholder syntax for automatic state injection:
  - {health_analysis} - From ReportAnalyst output
  - {user_profile} - From initial state
  - {validation_result} - From SafetyGuard feedback on retry

Logging:
- Agent creation is logged in orchestrator during workflow initialization
- Execution tracing with iteration number is handled by orchestrator.execute()
"""

from google.adk.agents import LlmAgent

from ..ai import load_prompt
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
    def create_agent(model_name: str = "gemini-2.5-flash") -> LlmAgent:
        """Create ADK LlmAgent for lifestyle plan generation.

        Args:
            model_name: Gemini model name (default: gemini-2.5-flash)

        Returns:
            Configured LlmAgent instance
        """
        # Load system prompt from external file
        system_prompt = load_prompt("planner_prompt")

        logger.info(
            "LifestylePlanner agent created",
            model=model_name,
            output_key="current_plan",
            description="Generates personalized lifestyle plans from health metrics",
            state_injection_fields=["health_analysis", "user_profile", "validation_result"]
        )

        # Add state injection placeholders
        enhanced_prompt = f"""{system_prompt}

# Context
You will receive health analysis results and user profile information.

## Health Analysis (from ReportAnalyst)
{{health_analysis}}

## User Profile
{{user_profile}}

## Previous Feedback (if this is a retry)
{{validation_result}}

# Instructions
1. Generate a personalized Markdown lifestyle plan based on the health analysis
2. Address all identified risk tags
3. Keep the plan under 1500 words
4. Include medical disclaimers
5. Cite credible sources for medical recommendations
6. If feedback is provided, incorporate it to improve the plan
7. MUST include disclaimer: "This plan is for informational purposes only. Always consult with your healthcare provider before making significant lifestyle changes."
"""

        return LlmAgent(
            name="LifestylePlanner",
            model=model_name,
            instruction=enhanced_prompt,
            output_key="current_plan",
            description="Generates personalized lifestyle plans from health metrics"
        )

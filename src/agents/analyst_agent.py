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

        # Add structured output instructions
        enhanced_prompt = f"""{system_prompt}

# Input Format
You will receive a health report as JSON.

# Output Format
You MUST return a JSON object with exactly this structure:
{{
    "health_metrics": {{
        "cholesterol_total": <number>,
        "cholesterol_ldl": <number>,
        "cholesterol_hdl": <number>,
        "blood_pressure_systolic": <number>,
        "blood_pressure_diastolic": <number>,
        "glucose": <number>,
        "bmi": <number>
    }},
    "risk_tags": [<list of risk tag strings>]
}}

Risk tags should include:
- "high_cholesterol" if total cholesterol > 200
- "high_ldl" if LDL > 130
- "high_blood_pressure" if systolic > 130 or diastolic > 80
- "elevated_glucose" if glucose > 100
- "overweight" if BMI > 25
- "obese" if BMI > 30
"""

        return LlmAgent(
            name="ReportAnalyst",
            model=model_name,
            instruction=enhanced_prompt,
            output_key="health_analysis",
            description="Parses health reports into structured metrics and risk tags"
        )

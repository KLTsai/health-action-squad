"""SafetyGuardAgent - Plan validation and safety checking agent.

Validates lifestyle plans against safety policies using Google ADK.

Safety Rules:
- Loads safety policies from resources/policies/safety_rules.yaml
- Validates against all rules before approving plan
- Provides structured feedback for rejection cases

Logging:
- Logs safety rules loading
- Execution tracing with approval/rejection decisions handled by orchestrator
"""

import yaml
from google.adk.agents import LlmAgent
from google.adk.tools.exit_loop_tool import exit_loop
from google.adk.tools import FunctionTool

from ..ai import load_prompt
from ..common.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SafetyGuardAgent:
    """Factory for creating SafetyGuard ADK agent.

    Responsibilities:
    - Validate current_plan against safety_rules.yaml
    - Check for medical claims without sources
    - Detect potentially harmful recommendations
    - Return: decision (APPROVE/REJECT), feedback, violations
    - On REJECT: provide specific feedback for Planner retry
    - On APPROVE: call approve_and_exit tool to terminate loop

    System prompt loaded from: resources/prompts/guard_prompt.txt
    Safety rules loaded from: resources/policies/safety_rules.yaml
    """

    @staticmethod
    def create_agent(model_name: str = "gemini-2.5-flash") -> LlmAgent:
        """Create ADK LlmAgent for safety validation.

        Args:
            model_name: Gemini model name (default: gemini-2.5-flash)

        Returns:
            Configured LlmAgent instance with termination tool
        """
        # Load system prompt from external file
        system_prompt = load_prompt("guard_prompt")

        # Load safety rules from YAML
        safety_rules = SafetyGuardAgent._load_safety_rules()

        logger.info(
            "SafetyGuard agent created",
            model=model_name,
            output_key="validation_result",
            description="Validates plans against safety policies and terminates loop on approval",
            tools=["exit_loop"]
        )

        # Inject dynamic safety rules into the loaded prompt
        safety_rules_yaml = yaml.dump(safety_rules, default_flow_style=False)
        enhanced_prompt = system_prompt.replace(
            "{safety_rules_yaml}",
            f"```yaml\n{safety_rules_yaml}```"
        )

        return LlmAgent(
            name="SafetyGuard",
            model=model_name,
            instruction=enhanced_prompt,
            output_key="validation_result",
            tools=[FunctionTool(exit_loop)],  # Use ADK's built-in exit_loop tool
            description="Validates plans against safety policies and terminates loop on approval"
        )

    @staticmethod
    def _load_safety_rules() -> dict:
        """Load safety rules from resources/policies/safety_rules.yaml.

        Returns:
            Safety rules dictionary

        Raises:
            FileNotFoundError: If safety rules file doesn't exist
        """
        if not Config.SAFETY_RULES_PATH.exists():
            logger.error(
                "Safety rules file not found",
                rules_path=str(Config.SAFETY_RULES_PATH)
            )
            raise FileNotFoundError(
                f"Safety rules not found: {Config.SAFETY_RULES_PATH}"
            )

        with Config.SAFETY_RULES_PATH.open("r", encoding="utf-8") as f:
            safety_rules = yaml.safe_load(f)

        logger.info(
            "Safety rules loaded",
            rules_path=str(Config.SAFETY_RULES_PATH),
            rule_count=len(safety_rules) if safety_rules else 0
        )

        return safety_rules

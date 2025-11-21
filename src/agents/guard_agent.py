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
            model_name: Gemini model name (default: gemini-pro)

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

        # Add validation instructions with tool usage
        enhanced_prompt = f"""{system_prompt}

# Safety Rules (from safety_rules.yaml)
```yaml
{yaml.dump(safety_rules, default_flow_style=False)}
```

# Context
You will receive the generated lifestyle plan.

## Current Plan
{{current_plan}}

## Risk Tags
{{health_analysis}}

# Validation Instructions
1. Check plan against all safety rules
2. Verify medical claims are properly sourced
3. Check for appropriate disclaimers
4. Verify plan length is under 1500 words
5. Ensure risk-specific recommendations are present

# Decision Making
If the plan passes all checks:
- Decision: APPROVE
- **IMPORTANT**: Call the exit_loop tool to signal completion and terminate the retry loop
- Provide brief positive feedback

If the plan has violations:
- Decision: REJECT
- List specific violations
- Provide actionable feedback for improvement
- Do NOT call exit_loop

# Output Format
Always return JSON:
{{
    "decision": "APPROVE" or "REJECT",
    "feedback": ["list of feedback items"],
    "violations": ["list of violations if any"]
}}

Then if APPROVED, call exit_loop tool to terminate the loop.
"""

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

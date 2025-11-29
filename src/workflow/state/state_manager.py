"""State manager for session state preparation.

Handles all state-related logic including loading external resources.
"""

from typing import Dict, Any
import yaml

from ...common.config import Config
from ...utils.logger import get_logger

logger = get_logger(__name__)


class StateManager:
    """Manages session state preparation and external resource loading.

    High Cohesion:
    - All state-related logic centralized
    - Encapsulates state structure knowledge
    - Handles external resource loading (YAML, etc.)

    Low Coupling:
    - No dependency on workflow execution
    - No dependency on agents
    - Can be used and tested independently

    Responsibility:
    - Define initial state structure
    - Load external resources (safety rules, etc.)
    - Validate state completeness

    NOT responsible for:
    - Workflow execution
    - Agent creation
    - Response formatting
    """

    @staticmethod
    def prepare_initial_state(
        health_report: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare complete initial session state.

        This is the SINGLE SOURCE OF TRUTH for initial state structure.
        All state keys used in prompts must be defined here.

        Args:
            health_report: User's health report data
            user_profile: User profile information

        Returns:
            Complete initial state dictionary with all required keys

        Note:
            State keys correspond to placeholders in agent prompts:
            - {health_report} → health_report
            - {user_profile} → user_profile
            - {health_analysis} → health_analysis (from ReportAnalyst)
            - {current_plan} → current_plan (from LifestylePlanner)
            - {validation_result} → validation_result (from SafetyGuard)
            - {safety_rules_yaml} → safety_rules_yaml (static resource)
        """
        # Load external resources
        safety_rules_yaml = StateManager._load_safety_rules()

        # Define complete initial state
        initial_state = {
            "user_profile": user_profile,
            "health_report": health_report,
            "health_analysis": None,  # Will be populated by ReportAnalyst
            "current_plan": None,  # Will be populated by LifestylePlanner
            "validation_result": None,  # Will be populated by SafetyGuard
            "safety_rules_yaml": safety_rules_yaml,  # Static resource
        }

        logger.debug(
            "Initial state prepared",
            state_keys=list(initial_state.keys()),
            user_profile_present=bool(user_profile),
            health_report_present=bool(health_report),
            safety_rules_loaded=bool(safety_rules_yaml)
        )

        return initial_state

    @staticmethod
    def _load_safety_rules() -> str:
        """Load safety rules from YAML file.

        Private method - encapsulates file loading details.
        This is the ONLY place where safety_rules.yaml is loaded.

        Returns:
            Formatted YAML string for prompt injection

        Raises:
            FileNotFoundError: If safety rules file doesn't exist
        """
        rules_path = Config.SAFETY_RULES_PATH

        if not rules_path.exists():
            logger.error(
                "Safety rules file not found",
                rules_path=str(rules_path)
            )
            raise FileNotFoundError(
                f"Safety rules not found: {rules_path}"
            )

        # Load YAML content
        with rules_path.open("r", encoding="utf-8") as f:
            safety_rules = yaml.safe_load(f)

        # Convert to formatted YAML string
        safety_rules_yaml = yaml.dump(safety_rules, default_flow_style=False)

        logger.info(
            "Safety rules loaded",
            rules_path=str(rules_path),
            yaml_length=len(safety_rules_yaml)
        )

        # Wrap in markdown code block for better LLM parsing
        return f"```yaml\n{safety_rules_yaml}```"

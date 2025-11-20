"""SafetyGuardAgent - Plan validation and safety checking agent.

Validates lifestyle plans against safety policies.
MUST inherit from google.adk.agents.Agent.
"""

from typing import Dict, List
import yaml
# from google.adk.agents import Agent  # Uncomment when ADK is installed

from ..core.state import SessionState, WorkflowStatus
from ..core.config import Config
from ..utils.logger import AgentLogger


class SafetyGuardAgent:  # TODO: Inherit from Agent when ADK is installed
    """SafetyGuardAgent validates plans against safety policies.

    Responsibilities:
    - Validate current_plan against safety_rules.yaml
    - Check for medical claims without sources
    - Detect potentially harmful recommendations
    - Return: decision (APPROVE/REJECT), feedback, violations
    - On REJECT: provide specific feedback for Planner retry
    - Max 3 retry attempts enforced by Orchestrator

    System prompt loaded from: resources/prompts/guard_prompt.txt
    Safety rules loaded from: resources/policies/safety_rules.yaml
    """

    def __init__(self):
        """Initialize SafetyGuardAgent."""
        self.config = Config()
        self.logger = AgentLogger("SafetyGuardAgent")

        # Load system prompt from file (NOT hardcoded)
        self.system_prompt = self._load_prompt()

        # Load safety rules from YAML (NOT hardcoded)
        self.safety_rules = self._load_safety_rules()

        self.logger.info("SafetyGuardAgent initialized")

    def _load_prompt(self) -> str:
        """Load system prompt from resources/prompts/guard_prompt.txt.

        Returns:
            System prompt text
        """
        return Config.get_prompt(Config.GUARD_PROMPT_PATH)

    def _load_safety_rules(self) -> Dict:
        """Load safety rules from resources/policies/safety_rules.yaml.

        Returns:
            Safety rules dictionary

        Raises:
            FileNotFoundError: If safety rules file doesn't exist
        """
        if not Config.SAFETY_RULES_PATH.exists():
            raise FileNotFoundError(
                f"Safety rules not found: {Config.SAFETY_RULES_PATH}"
            )

        with Config.SAFETY_RULES_PATH.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def execute(self, state: SessionState) -> SessionState:
        """Validate lifestyle plan against safety policies.

        Args:
            state: Current session state with current_plan and risk_tags

        Returns:
            Updated SessionState with validation decision and feedback

        Raises:
            ValueError: If current_plan is empty
        """
        self.logger.set_session(state.session_id)
        self.logger.set_iteration(state.retry_count + 1)

        self.logger.info(
            "Starting plan validation",
            iteration=state.retry_count + 1,
            plan_length=len(state.current_plan)
        )

        # Validate input
        if not state.current_plan:
            raise ValueError("Cannot validate empty plan")

        # TODO: Implement ADK agent execution
        # 1. Use ADK ModelClient to call Gemini
        # 2. Pass system_prompt, current_plan, risk_tags, and safety_rules
        # 3. Get validation decision and detailed feedback

        # Placeholder implementation
        validation_result = self._validate_plan_placeholder(state)

        # Update state based on decision
        if validation_result["decision"] == "APPROVE":
            updated_state = state.update(status=WorkflowStatus.APPROVED)

            self.logger.info(
                "Plan approved",
                iteration=state.retry_count + 1
            )
        else:
            # Add feedback to history
            feedback_entry = {
                "iteration": state.retry_count + 1,
                "decision": validation_result["decision"],
                "feedback": validation_result["feedback"],
                "violations": validation_result["violations"],
            }

            feedback_history = state.feedback_history + [feedback_entry]

            updated_state = state.update(
                feedback_history=feedback_history,
                status=WorkflowStatus.PLANNING  # Back to planning
            )

            self.logger.warning(
                "Plan rejected",
                iteration=state.retry_count + 1,
                violations=validation_result["violations"]
            )

        self.logger.trace_state_transition(
            from_state=state.status.value,
            to_state=updated_state.status.value,
            decision=validation_result["decision"]
        )

        return updated_state

    def _validate_plan_placeholder(self, state: SessionState) -> Dict:
        """Placeholder for plan validation.

        TODO: Replace with actual ADK agent implementation.

        Args:
            state: Current session state

        Returns:
            Validation result dictionary with decision, feedback, violations
        """
        plan = state.current_plan
        risk_tags = state.risk_tags

        # Perform basic rule-based validation
        violations = []
        feedback = []

        # Check 1: Plan length
        if len(plan) > Config.PLAN_MAX_LENGTH:
            violations.append("plan_too_long")
            feedback.append(f"Plan exceeds maximum length of {Config.PLAN_MAX_LENGTH} characters")

        # Check 2: Disclaimer present
        if "disclaimer" not in plan.lower() and "consult" not in plan.lower():
            violations.append("missing_disclaimer")
            feedback.append("Plan must include medical disclaimer and recommendation to consult healthcare provider")

        # Check 3: Medical claims with sources
        medical_keywords = ["treatment", "cure", "medication", "diagnosis"]
        has_medical_claims = any(keyword in plan.lower() for keyword in medical_keywords)
        has_sources = "source" in plan.lower() or "reference" in plan.lower()

        if has_medical_claims and not has_sources:
            violations.append("unsourced_medical_claims")
            feedback.append("Medical claims must be supported with credible sources")

        # Check 4: Risk-specific validation
        if "high_blood_pressure" in risk_tags:
            if "reduce sodium" not in plan.lower() and "salt" not in plan.lower():
                violations.append("missing_risk_mitigation")
                feedback.append("Plan should address sodium reduction for high blood pressure")

        # Decide based on violations
        if not violations:
            decision = "APPROVE"
            feedback = ["Plan meets all safety requirements"]
        else:
            decision = "REJECT"

        return {
            "decision": decision,
            "feedback": feedback,
            "violations": violations,
        }

    def get_safety_rules(self) -> Dict:
        """Get loaded safety rules.

        Returns:
            Safety rules dictionary
        """
        return self.safety_rules

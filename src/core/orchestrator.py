"""Main orchestrator for Health Action Squad workflow.

Coordinates the Analyst → Planner → Guard loop with circuit breaker protection.
"""

from typing import Dict, Optional
import uuid
from datetime import datetime

from .state import SessionState, WorkflowStatus, MAX_RETRIES
from .config import Config
from ..utils.logger import get_logger

# Agent imports will be added when agents are implemented
# from ..agents.analyst_agent import ReportAnalystAgent
# from ..agents.planner_agent import LifestylePlannerAgent
# from ..agents.guard_agent import SafetyGuardAgent


logger = get_logger(__name__)


class Orchestrator:
    """Main workflow orchestrator.

    Manages the multi-agent workflow:
    1. ReportAnalystAgent parses health report
    2. LifestylePlannerAgent generates plan
    3. SafetyGuardAgent validates plan
    4. Loop back to Planner if rejected (max MAX_RETRIES)
    5. Return approved plan or fallback

    All communication happens through immutable SessionState.
    """

    def __init__(self):
        """Initialize orchestrator and agents."""
        self.config = Config()
        self.logger = logger

        # Initialize agents (will be uncommented when agents are implemented)
        # self.analyst = ReportAnalystAgent()
        # self.planner = LifestylePlannerAgent()
        # self.guard = SafetyGuardAgent()

        self.logger.info("Orchestrator initialized")

    def execute(self, health_report: Dict, user_profile: Optional[Dict] = None) -> Dict:
        """Execute the full workflow.

        Args:
            health_report: Raw health report data
            user_profile: Optional user profile data

        Returns:
            Dict with final plan and metadata

        Raises:
            Exception: If workflow fails critically
        """
        # Initialize session
        session_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        state = SessionState(
            session_id=session_id,
            timestamp=timestamp,
            user_profile=user_profile or {},
            status=WorkflowStatus.INIT,
        )

        self.logger.info(
            "Workflow started",
            extra={"session_id": session_id, "timestamp": timestamp}
        )

        try:
            # Step 1: Analyze health report
            state = self._analyze_report(state, health_report)

            # Step 2: Planner-Guard loop with circuit breaker
            state = self._planning_loop(state)

            # Step 3: Return final result
            return self._format_output(state)

        except Exception as e:
            self.logger.error(
                "Workflow failed",
                extra={
                    "session_id": session_id,
                    "error": str(e),
                    "status": state.status.value
                }
            )
            # Return fallback result
            return self._generate_fallback(state)

    def _analyze_report(self, state: SessionState, health_report: Dict) -> SessionState:
        """Run ReportAnalystAgent to parse health report.

        Args:
            state: Current session state
            health_report: Raw health report data

        Returns:
            Updated SessionState with health_metrics and risk_tags
        """
        self.logger.info("Starting report analysis", extra={"session_id": state.session_id})

        state = state.update(status=WorkflowStatus.ANALYZING)

        # TODO: Implement when ReportAnalystAgent is ready
        # result = self.analyst.execute(state, health_report)
        # state = state.update(
        #     health_metrics=result.health_metrics,
        #     risk_tags=result.risk_tags,
        #     status=WorkflowStatus.PLANNING
        # )

        # Placeholder for now
        state = state.update(
            health_metrics={"placeholder": "metrics"},
            risk_tags=["placeholder_risk"],
            status=WorkflowStatus.PLANNING
        )

        self.logger.info(
            "Report analysis completed",
            extra={
                "session_id": state.session_id,
                "risk_tags": state.risk_tags
            }
        )

        return state

    def _planning_loop(self, state: SessionState) -> SessionState:
        """Execute Planner-Guard loop with circuit breaker.

        Args:
            state: Current session state

        Returns:
            Updated SessionState with approved plan or fallback
        """
        self.logger.info(
            "Starting planning loop",
            extra={"session_id": state.session_id, "max_retries": MAX_RETRIES}
        )

        while state.retry_count < MAX_RETRIES:
            self.logger.info(
                "Planning iteration",
                extra={
                    "session_id": state.session_id,
                    "iteration": state.retry_count + 1,
                    "max_retries": MAX_RETRIES
                }
            )

            # Generate plan
            state = self._generate_plan(state)

            # Validate plan
            state = self._validate_plan(state)

            # Check if approved
            if state.status == WorkflowStatus.APPROVED:
                self.logger.info(
                    "Plan approved",
                    extra={
                        "session_id": state.session_id,
                        "iterations": state.retry_count + 1
                    }
                )
                return state

            # Increment retry counter
            state = state.update(retry_count=state.retry_count + 1)

        # Circuit breaker triggered
        self.logger.warning(
            "Circuit breaker triggered - max retries exceeded",
            extra={
                "session_id": state.session_id,
                "retry_count": state.retry_count
            }
        )

        state = state.update(status=WorkflowStatus.FAILED)
        return state

    def _generate_plan(self, state: SessionState) -> SessionState:
        """Run LifestylePlannerAgent to generate plan.

        Args:
            state: Current session state

        Returns:
            Updated SessionState with current_plan
        """
        # TODO: Implement when LifestylePlannerAgent is ready
        # plan = self.planner.execute(state)
        # state = state.update(current_plan=plan)

        # Placeholder
        state = state.update(
            current_plan="# Placeholder Lifestyle Plan\n\nThis will be generated by LifestylePlannerAgent"
        )

        return state

    def _validate_plan(self, state: SessionState) -> SessionState:
        """Run SafetyGuardAgent to validate plan.

        Args:
            state: Current session state

        Returns:
            Updated SessionState with validation result
        """
        state = state.update(status=WorkflowStatus.REVIEWING)

        # TODO: Implement when SafetyGuardAgent is ready
        # result = self.guard.execute(state)
        #
        # if result.decision == "APPROVE":
        #     state = state.update(status=WorkflowStatus.APPROVED)
        # else:
        #     feedback = {
        #         "iteration": state.retry_count + 1,
        #         "decision": result.decision,
        #         "feedback": result.feedback,
        #         "violations": result.violations
        #     }
        #     feedback_history = state.feedback_history + [feedback]
        #     state = state.update(feedback_history=feedback_history)

        # Placeholder - approve after first iteration
        if state.retry_count == 0:
            state = state.update(status=WorkflowStatus.APPROVED)
        else:
            state = state.update(status=WorkflowStatus.PLANNING)

        return state

    def _format_output(self, state: SessionState) -> Dict:
        """Format final output.

        Args:
            state: Final session state

        Returns:
            Formatted output dictionary
        """
        return {
            "session_id": state.session_id,
            "timestamp": state.timestamp,
            "status": state.status.value,
            "plan": state.current_plan,
            "health_metrics": state.health_metrics,
            "risk_tags": state.risk_tags,
            "iterations": state.retry_count + 1,
            "feedback_history": state.feedback_history,
        }

    def _generate_fallback(self, state: SessionState) -> Dict:
        """Generate fallback response when workflow fails.

        Args:
            state: Current session state

        Returns:
            Fallback response dictionary
        """
        fallback_plan = self._create_safe_fallback_plan(state.risk_tags)

        return {
            "session_id": state.session_id,
            "timestamp": state.timestamp,
            "status": "fallback",
            "plan": fallback_plan,
            "risk_tags": state.risk_tags,
            "message": "Unable to generate personalized plan. Providing safe general recommendations.",
            "error": state.error_message or "Max retries exceeded"
        }

    def _create_safe_fallback_plan(self, risk_tags: list) -> str:
        """Create safe generic advice as fallback.

        Args:
            risk_tags: List of identified risk tags

        Returns:
            Safe fallback plan in Markdown
        """
        return """# General Health Recommendations

⚠️ **Note**: This is a general recommendation. Please consult with a healthcare provider for personalized advice.

## General Guidelines

1. **Physical Activity**
   - Aim for at least 150 minutes of moderate aerobic activity per week
   - Include strength training exercises 2+ times per week
   - Start slowly and gradually increase intensity

2. **Nutrition**
   - Follow a balanced diet with fruits, vegetables, whole grains, and lean proteins
   - Stay hydrated with adequate water intake
   - Limit processed foods, added sugars, and excessive salt

3. **Sleep**
   - Aim for 7-9 hours of quality sleep per night
   - Maintain a consistent sleep schedule
   - Create a relaxing bedtime routine

4. **Stress Management**
   - Practice relaxation techniques (meditation, deep breathing)
   - Engage in activities you enjoy
   - Maintain social connections

5. **Medical Care**
   - Schedule regular check-ups with your healthcare provider
   - Follow prescribed treatments and medications
   - Report any concerning symptoms promptly

**⚠️ Important**: This plan is not a substitute for professional medical advice. Please consult your healthcare provider before making significant lifestyle changes.
"""

"""Main orchestrator for Health Action Squad workflow.

Coordinates the Analyst → Planner → Guard loop with circuit breaker protection.
Uses Google ADK declarative workflow patterns.
"""

from typing import Dict, Optional
import uuid
from datetime import datetime

from google.adk.agents import SequentialAgent, LoopAgent

from ..domain.state import SessionState, WorkflowStatus, MAX_RETRIES
from ..common.config import Config
from ..utils.logger import get_logger
from ..agents.analyst_agent import ReportAnalystAgent
from ..agents.planner_agent import LifestylePlannerAgent
from ..agents.guard_agent import SafetyGuardAgent


logger = get_logger(__name__)


class Orchestrator:
    """Main workflow orchestrator using Google ADK.

    ADK Workflow Structure:
    1. SequentialAgent orchestrates:
       a. ReportAnalyst (parse health report)
       b. LoopAgent (Planner ↔ Guard retry loop)
    2. LoopAgent manages Planner → Guard with max_iterations=MAX_RETRIES
    3. Guard calls exit_loop tool when plan is approved
    4. State flows through agent output_keys automatically

    All communication happens through ADK's state management.
    """

    def __init__(self, model_name: str = "gemini-pro"):
        """Initialize orchestrator with ADK workflow.

        Args:
            model_name: Gemini model name (default: gemini-pro)
        """
        self.config = Config()
        self.logger = logger
        self.model_name = model_name

        # Create ADK agents
        self.analyst_agent = ReportAnalystAgent.create_agent(model_name)
        self.planner_agent = LifestylePlannerAgent.create_agent(model_name)
        self.guard_agent = SafetyGuardAgent.create_agent(model_name)

        # Create Planner-Guard retry loop
        self.planning_loop = LoopAgent(
            name="PlanningLoop",
            sub_agents=[self.planner_agent, self.guard_agent],
            max_iterations=MAX_RETRIES,
            description=f"Planner-Guard retry loop with max {MAX_RETRIES} iterations"
        )

        # Create main sequential workflow
        self.workflow = SequentialAgent(
            name="HealthActionSquad",
            sub_agents=[self.analyst_agent, self.planning_loop],
            description="Health report analysis → lifestyle plan generation with safety validation"
        )

        self.logger.info(
            "ADK Orchestrator initialized",
            extra={
                "model": model_name,
                "workflow": "SequentialAgent[Analyst, LoopAgent[Planner, Guard]]"
            }
        )

    async def execute(self, health_report: Dict, user_profile: Optional[Dict] = None) -> Dict:
        """Execute the ADK workflow.

        Args:
            health_report: Raw health report data (will be passed to Analyst)
            user_profile: Optional user profile data

        Returns:
            Dict with final plan and metadata from ADK workflow

        Raises:
            Exception: If workflow fails critically
        """
        # Initialize session
        session_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        self.logger.info(
            "ADK Workflow started",
            extra={
                "session_id": session_id,
                "timestamp": timestamp,
                "model": self.model_name
            }
        )

        try:
            # Prepare initial state for ADK workflow
            initial_state = {
                "session_id": session_id,
                "timestamp": timestamp,
                "user_profile": user_profile or {},
                "health_report": health_report,  # For Analyst to process
            }

            # Execute ADK workflow (SequentialAgent handles orchestration)
            result = await self.workflow.run(initial_state)

            # ADK automatically manages state flow through output_keys:
            # - Analyst outputs to "health_analysis"
            # - Planner outputs to "current_plan"
            # - Guard outputs to "validation_result"

            self.logger.info(
                "ADK Workflow completed",
                extra={
                    "session_id": session_id,
                    "workflow_status": "success"
                }
            )

            return self._format_adk_output(result, session_id, timestamp)

        except Exception as e:
            self.logger.error(
                "ADK Workflow failed",
                extra={
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
            )
            # Return fallback result
            return self._generate_fallback_from_error(session_id, timestamp, str(e))

    def _format_adk_output(self, adk_result: Dict, session_id: str, timestamp: str) -> Dict:
        """Format ADK workflow output into standard response.

        Args:
            adk_result: Result dict from ADK workflow execution
            session_id: Session identifier
            timestamp: Execution timestamp

        Returns:
            Formatted output dictionary
        """
        return {
            "session_id": session_id,
            "timestamp": timestamp,
            "status": "approved",  # If we got here, Guard approved the plan
            "plan": adk_result.get("current_plan", ""),
            "health_analysis": adk_result.get("health_analysis", {}),
            "validation_result": adk_result.get("validation_result", {}),
            "workflow_type": "adk",
            "model": self.model_name,
        }

    def _generate_fallback_from_error(
        self, session_id: str, timestamp: str, error: str
    ) -> Dict:
        """Generate fallback response when ADK workflow fails.

        Args:
            session_id: Session identifier
            timestamp: Execution timestamp
            error: Error message

        Returns:
            Fallback response dictionary
        """
        fallback_plan = self._create_safe_fallback_plan([])

        return {
            "session_id": session_id,
            "timestamp": timestamp,
            "status": "fallback",
            "plan": fallback_plan,
            "message": "Unable to generate personalized plan. Providing safe general recommendations.",
            "error": error,
            "workflow_type": "adk",
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

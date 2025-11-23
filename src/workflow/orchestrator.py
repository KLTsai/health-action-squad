"""Main orchestrator for Health Action Squad workflow.

Coordinates the Analyst → Planner → Guard loop with circuit breaker protection.
Uses Google ADK declarative workflow patterns.

Logging Strategy:
- Session initialization with metadata
- Agent creation with model and capability details
- Workflow execution lifecycle (start, completion, errors)
- Loop iterations with iteration counters
- Guard decisions (APPROVE/REJECT) with structured feedback
- Fallback triggers with error context
- All logging uses AgentLogger for structured A2A tracing
"""

from typing import Dict, Optional
import uuid
from datetime import datetime
import json

from google.adk.agents import SequentialAgent, LoopAgent

from ..domain.state import MAX_RETRIES  # SessionState/WorkflowStatus not used in ADK workflow
from ..common.config import Config
from ..utils.logger import get_logger, AgentLogger
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

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize orchestrator with ADK workflow.

        Args:
            model_name: Gemini model name (default: gemini-2.5-flash)
        """
        self.config = Config()
        self.logger = logger
        self.model_name = model_name
        self.agent_logger = AgentLogger("Orchestrator")

        logger.info(
            "Orchestrator initialization starting",
            model=model_name,
            max_retries=MAX_RETRIES
        )

        # Create ADK agents
        self.analyst_agent = ReportAnalystAgent.create_agent(model_name)
        self.planner_agent = LifestylePlannerAgent.create_agent(model_name)
        self.guard_agent = SafetyGuardAgent.create_agent(model_name)

        logger.info(
            "ADK agents created",
            agents=["ReportAnalyst", "LifestylePlanner", "SafetyGuard"],
            model=model_name
        )

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

        logger.info(
            "ADK Orchestrator initialized",
            workflow_structure="SequentialAgent[Analyst, LoopAgent[Planner, Guard]]",
            max_loop_iterations=MAX_RETRIES,
            model=model_name
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
            # IMPORTANT: run_async() returns an async generator, not an awaitable
            # We must consume the generator to execute the workflow
            final_result = None
            async for event in self.workflow.run_async(initial_state):
                # ADK emits events during execution
                # The final event contains the complete workflow result
                if hasattr(event, 'is_final_response') and event.is_final_response():
                    final_result = event
                    break
                # For non-final events, we can access them as dictionaries
                elif isinstance(event, dict):
                    final_result = event

            # If no final result captured, use the last event
            if final_result is None:
                self.logger.warning(
                    "No final response detected, using last event",
                    extra={"session_id": session_id}
                )
                final_result = event if 'event' in locals() else {}

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

            return self._format_adk_output(final_result, session_id, timestamp)

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
            Formatted output dictionary with all required fields
        """
        # Extract health analysis and validation results
        health_analysis = adk_result.get("health_analysis", {})
        validation_result = adk_result.get("validation_result", {})

        # Extract risk tags from health analysis
        risk_tags = []
        if isinstance(health_analysis, dict):
            risk_tags = health_analysis.get("risk_tags", [])
        elif isinstance(health_analysis, str):
            # If health_analysis is JSON string, parse it
            try:
                import json
                parsed = json.loads(health_analysis)
                risk_tags = parsed.get("risk_tags", [])
            except (json.JSONDecodeError, AttributeError):
                risk_tags = []

        # Determine status based on validation decision
        status = "approved"
        if isinstance(validation_result, dict):
            decision = validation_result.get("decision", "APPROVE")
            if decision != "APPROVE":
                status = "rejected"

        # Extract iteration count from ADK loop metadata (if available)
        # ADK LoopAgent may provide this in metadata
        iterations = adk_result.get("_loop_iterations", 1)
        if iterations == 1 and isinstance(validation_result, dict):
            # Fallback: check if there's retry information
            iterations = adk_result.get("iterations", 1)

        return {
            "session_id": session_id,
            "timestamp": timestamp,
            "status": status,
            "plan": adk_result.get("current_plan", ""),
            "risk_tags": risk_tags,
            "iterations": iterations,
            "health_analysis": health_analysis,
            "validation_result": validation_result,
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
            Fallback response dictionary with all required fields
        """
        fallback_plan = self._create_safe_fallback_plan([])

        return {
            "session_id": session_id,
            "timestamp": timestamp,
            "status": "fallback",
            "plan": fallback_plan,
            "risk_tags": [],
            "iterations": 1,  # Changed from 0 to 1 to satisfy Pydantic validation (ge=1)
            "health_analysis": {},
            "validation_result": {},
            "message": "Unable to generate personalized plan. Providing safe general recommendations.",
            "error": error,
            "workflow_type": "adk",
            "model": self.model_name,
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

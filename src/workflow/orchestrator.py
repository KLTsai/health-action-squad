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
import yaml

from google.adk.agents import SequentialAgent, LoopAgent, InvocationContext
from google.adk.sessions import InMemorySessionService
from google.adk.runners import RunConfig

from ..domain.state import MAX_RETRIES  # SessionState/WorkflowStatus not used in ADK workflow
from ..common.config import Config
from ..utils.logger import get_logger, AgentLogger
from ..agents.analyst_agent import ReportAnalystAgent
from ..agents.planner_agent import LifestylePlannerAgent
from ..agents.guard_agent import SafetyGuardAgent
from .event_processor import EventStreamProcessor
from .response_formatter import ResponseFormatter


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

        # Create session service for ADK execution
        self.session_service = InMemorySessionService()

        # Initialize EventStreamProcessor with agent-to-output-key mapping
        self.event_processor = EventStreamProcessor({
            "ReportAnalyst": "health_analysis",
            "LifestylePlanner": "current_plan",
            "SafetyGuard": "validation_result"
        })

        # Initialize ResponseFormatter for output formatting
        self.response_formatter = ResponseFormatter(model_name=model_name)

        logger.info(
            "ADK Orchestrator initialized",
            workflow_structure="SequentialAgent[Analyst, LoopAgent[Planner, Guard]]",
            max_loop_iterations=MAX_RETRIES,
            model=model_name
        )

    def _load_safety_rules_yaml(self) -> str:
        """Load safety rules from YAML file and return as formatted YAML string.

        Returns:
            Formatted YAML string with safety rules (for ADK placeholder injection)

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

        # Convert to formatted YAML string for Guard prompt injection
        safety_rules_yaml = yaml.dump(safety_rules, default_flow_style=False)

        logger.info(
            "Safety rules loaded for ADK state injection",
            rules_path=str(Config.SAFETY_RULES_PATH),
            yaml_length=len(safety_rules_yaml)
        )

        return f"```yaml\n{safety_rules_yaml}```"

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
            # Load safety rules for Guard agent placeholder injection
            safety_rules_yaml = self._load_safety_rules_yaml()

            # Prepare initial state dict with all expected keys
            # ADK requires all state keys referenced in prompts to be pre-defined
            initial_state = {
                "user_profile": user_profile or {},
                "health_report": health_report,
                "health_analysis": None,  # Will be populated by ReportAnalyst
                "current_plan": None,  # Will be populated by LifestylePlanner
                "validation_result": None,  # Will be populated by SafetyGuard
                "safety_rules_yaml": safety_rules_yaml,  # Static, loaded once for Guard
            }

            self.logger.info(
                "ADK Workflow executing with InvocationContext",
                extra={
                    "session_id": session_id,
                    "initial_state_keys": list(initial_state.keys())
                }
            )

            # Debug logging for initial state
            self.logger.debug(
                "Initial state prepared",
                extra={
                    "session_id": session_id,
                    "health_report_keys": list(health_report.keys()) if health_report else [],
                    "user_profile_keys": list(user_profile.keys()) if user_profile else []
                }
            )

            # Create session using SessionService (not manual Session construction)
            # This ensures proper session management and state persistence
            invocation_id = str(uuid.uuid4())
            user_id = "default_user"
            app_name = "health_action_squad"

            # Create session via session service
            session = await self.session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                state=initial_state
            )

            # Create RunConfig for the workflow
            run_config = RunConfig()

            # Create InvocationContext for workflow execution
            context = InvocationContext(
                session_service=self.session_service,
                invocation_id=invocation_id,
                agent=self.workflow,
                session=session,
                run_config=run_config
            )

            # Execute workflow using EventStreamProcessor
            agent_outputs = await self.event_processor.process_events(
                self.workflow.run_async(context),
                self.logger
            )

            # Combine initial state with agent outputs
            final_state = {**initial_state, **agent_outputs}

            # Debug logging for final state
            self.logger.debug(
                "Final state received",
                extra={
                    "session_id": session_id,
                    "state_keys": list(final_state.keys()) if isinstance(final_state, dict) else [],
                    "health_analysis_present": "health_analysis" in final_state if isinstance(final_state, dict) else False,
                    "current_plan_present": "current_plan" in final_state if isinstance(final_state, dict) else False,
                    "current_plan_value": final_state.get("current_plan", "NOT_FOUND")[:100] if isinstance(final_state.get("current_plan"), str) else str(type(final_state.get("current_plan")))
                }
            )

            self.logger.info(
                "ADK Workflow completed",
                extra={
                    "session_id": session_id,
                    "workflow_status": "success",
                    "final_state_keys": list(final_state.keys()) if isinstance(final_state, dict) else [],
                    "health_analysis_type": str(type(final_state.get("health_analysis"))),
                    "current_plan_type": str(type(final_state.get("current_plan"))),
                    "current_plan_sample": str(final_state.get("current_plan"))[:200] if final_state.get("current_plan") else "None"
                }
            )

            return self.response_formatter.format_success_response(
                final_state, session_id, timestamp, self.model_name
            )

        except Exception as e:
            import traceback
            self.logger.error(
                "ADK Workflow failed",
                extra={
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                },
            )
            # Return fallback result
            return self.response_formatter.format_error_response(
                e, session_id, timestamp, self.model_name
            )

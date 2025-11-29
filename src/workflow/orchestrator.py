"""Simplified WorkflowOrchestrator using clean architecture principles.

This orchestrator acts as a Facade, providing a simple interface while
delegating to specialized components with high cohesion and low coupling.

Architecture:
- High Cohesion: Each component has ONE clear responsibility
- Low Coupling: Components depend on abstractions, not concrete classes
- SOLID Principles: SRP, DIP, OCP all satisfied
- Design Patterns: Facade, Strategy, Factory, Dependency Injection
"""

from typing import Dict, Optional
import uuid
from datetime import datetime

from .executors.base import WorkflowExecutor
from .executors.runner_executor import RunnerBasedExecutor
from .factories.agent_factory import AgentFactory
from .state.state_manager import StateManager
from .builders.response_builder import ResponseBuilder
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """Facade for workflow execution with clean architecture.

    High Cohesion:
    - Focuses ONLY on coordinating components
    - No business logic - delegates everything to specialized components
    - Single responsibility: orchestrate workflow execution

    Low Coupling:
    - Depends on abstractions (WorkflowExecutor interface)
    - Components are injected (easily mocked for testing)
    - No tight binding to concrete implementations

    Design Patterns:
    - Facade: Simplifies complex subsystem for external clients
    - Dependency Injection: Components injected, not created internally
    - Strategy: Executor implementation is pluggable

    Backward Compatibility:
    - Constructor signature unchanged: Orchestrator(model_name)
    - execute() signature unchanged: execute(health_report, user_profile)
    - Response format unchanged
    - Existing API code needs NO changes
    """

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        executor: Optional[WorkflowExecutor] = None
    ):
        """Initialize orchestrator with dependency injection.

        Args:
            model_name: Model name for agents (backward compatible parameter)
            executor: Workflow executor (defaults to RunnerBasedExecutor)
                     Injected for testability - can be mocked

        Note:
            For backward compatibility, model_name is the first parameter.
            executor is optional and defaults to RunnerBasedExecutor.
        """
        self.model_name = model_name

        # Dependency Injection - executor can be mocked for testing
        self.executor = executor or RunnerBasedExecutor()

        # Create workflow once (reusable across executions)
        self.workflow = AgentFactory.create_workflow(model_name)

        # Initialize response builder
        self.response_builder = ResponseBuilder(model_name)

        logger.info(
            "Orchestrator initialized with clean architecture",
            model=model_name,
            executor_type=type(self.executor).__name__,
            workflow_structure="SequentialAgent[Analyst, LoopAgent[Planner, Guard]]",
            architecture="high_cohesion_low_coupling"
        )

    async def execute(
        self,
        health_report: Dict,
        user_profile: Optional[Dict] = None
    ) -> Dict:
        """Execute workflow and return response.

        This method is a thin coordinator - it delegates to specialized
        components for each responsibility. No business logic here.

        Flow:
        1. StateManager prepares initial state
        2. Executor executes workflow
        3. ResponseBuilder formats response

        Args:
            health_report: User's health report data
            user_profile: Optional user profile information

        Returns:
            Formatted response dictionary (structure unchanged from before)
            {
                "session_id": str,
                "status": "approved" | "rejected",
                "plan": str,
                "risk_tags": List[str],
                "health_analysis": Dict,
                "validation_result": Dict,
                ...
            }

        Note:
            This interface is 100% backward compatible.
            Existing API code requires NO changes.
        """
        # Generate identifiers
        session_id = str(uuid.uuid4())
        user_id = "default_user"
        timestamp = datetime.utcnow().isoformat()

        logger.info(
            "Workflow execution started",
            session_id=session_id,
            user_id=user_id,
            model=self.model_name
        )

        try:
            # Step 1: Prepare initial state (delegated to StateManager)
            # High cohesion: StateManager knows HOW to prepare state
            initial_state = StateManager.prepare_initial_state(
                health_report=health_report,
                user_profile=user_profile or {}
            )

            logger.debug(
                "Initial state prepared",
                session_id=session_id,
                state_keys=list(initial_state.keys())
            )

            # Step 2: Execute workflow (delegated to Executor)
            # Low coupling: We depend on WorkflowExecutor interface, not concrete class
            final_state = await self.executor.execute(
                workflow=self.workflow,
                initial_state=initial_state,
                session_id=session_id,
                user_id=user_id
            )

            logger.info(
                "Workflow execution completed",
                session_id=session_id,
                final_state_keys=list(final_state.keys()),
                health_analysis_present=final_state.get("health_analysis") is not None,
                current_plan_present=final_state.get("current_plan") is not None,
                validation_result_present=final_state.get("validation_result") is not None
            )

            # Step 3: Build response (delegated to ResponseBuilder)
            # High cohesion: ResponseBuilder knows HOW to format responses
            return self.response_builder.build_success_response(
                final_state, session_id, timestamp
            )

        except Exception as e:
            import traceback
            logger.error(
                "Workflow execution failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc()
            )

            # Build error response (delegated to ResponseBuilder)
            return self.response_builder.build_error_response(
                e, session_id, timestamp
            )

    async def cleanup(self) -> None:
        """Cleanup resources.

        Delegates cleanup to executor if needed.
        """
        await self.executor.cleanup()
        logger.debug("Orchestrator cleanup completed")

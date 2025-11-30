"""Runner-based workflow executor using ADK Runner.

This is the recommended execution strategy that properly handles
session state updates via ADK's built-in mechanisms.
"""

from typing import Dict, Any, Optional
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from .base import WorkflowExecutor
from ...utils.logger import get_logger

logger = get_logger(__name__)


class RunnerBasedExecutor(WorkflowExecutor):
    """ADK Runner-based workflow executor.

    High Cohesion:
    - All Runner-related logic encapsulated in one class
    - Focuses solely on workflow execution via Runner
    - No external concerns (state prep, response formatting, etc.)

    Low Coupling:
    - Depends only on WorkflowExecutor interface
    - No direct dependency on Orchestrator or other components
    - Can be tested independently with mock workflows

    Responsibility:
    - Create and configure ADK Runner
    - Execute workflow via Runner.run_async()
    - Return final session state

    NOT responsible for:
    - State preparation (StateManager's job)
    - Response formatting (ResponseBuilder's job)
    - Agent creation (AgentFactory's job)
    """

    def __init__(self, app_name: str = "health_action_squad"):
        """Initialize executor.

        Args:
            app_name: ADK application name for Runner configuration
        """
        self.app_name = app_name
        self.session_service = InMemorySessionService()
        self._runner: Optional[Runner] = None

        logger.info(
            "RunnerBasedExecutor initialized",
            app_name=app_name,
            executor_type="runner_based"
        )

    async def execute(
        self,
        workflow: Any,
        initial_state: Dict[str, Any],
        session_id: str,
        user_id: str,
        progress_callback: Any = None
    ) -> Dict[str, Any]:
        """Execute workflow via ADK Runner.

        This method is highly cohesive - it ONLY handles Runner execution.
        All other concerns are handled by other components.

        Args:
            workflow: ADK SequentialAgent workflow
            initial_state: Pre-prepared initial state
            session_id: Session identifier
            user_id: User identifier
            progress_callback: Optional async callback(str) for progress updates

        Returns:
            Final session state with all agent outputs

        Note:
            ADK Runner automatically handles:
            1. Event stream processing
            2. State delta application (output_key updates)
            3. Session state persistence
            This is why we use Runner - it eliminates manual event handling.
        """
        # Lazy initialize Runner with workflow
        if self._runner is None or self._runner.agent != workflow:
            self._runner = Runner(
                app_name=self.app_name,
                agent=workflow,
                session_service=self.session_service
            )
            logger.debug(
                "ADK Runner created",
                session_id=session_id,
                app_name=self.app_name
            )

        # Create session with initial state
        await self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
            state=initial_state
        )

        logger.info(
            "Session created for Runner execution",
            session_id=session_id,
            user_id=user_id,
            state_keys=list(initial_state.keys())
        )

        # Execute workflow via Runner
        # Pass health_report in the message for ReportAnalyst to process
        import json
        health_report_json = json.dumps(initial_state.get("health_report", {}), indent=2)
        message_text = f"Please analyze this health report and generate a personalized health plan:\n\n{health_report_json}"

        new_message = Content(parts=[Part(text=message_text)])

        event_count = 0
        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        ):
            event_count += 1

            # Optional: Log events for debugging
            if hasattr(event, 'author'):
                logger.debug(
                    f"Event from {event.author}",
                    session_id=session_id,
                    event_number=event_count
                )
                
                # Send progress update
                if progress_callback:
                    # Format a user-friendly message based on the event
                    # We can refine this based on actual event structure
                    msg = f"Step {event_count}: Processing..."
                    if event.author:
                        msg = f"{event.author} is working..."
                    
                    await progress_callback(msg)

        logger.info(
            "Runner execution completed",
            session_id=session_id,
            total_events=event_count
        )

        # Retrieve final session state (Runner has updated it)
        final_session = await self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id
        )

        final_state = final_session.state

        logger.debug(
            "Final state retrieved",
            session_id=session_id,
            final_state_keys=list(final_state.keys()),
            health_analysis_present=final_state.get("health_analysis") is not None,
            current_plan_present=final_state.get("current_plan") is not None,
            validation_result_present=final_state.get("validation_result") is not None
        )

        return final_state

    async def cleanup(self) -> None:
        """Cleanup Runner resources.

        Currently Runner doesn't require explicit cleanup, but this
        method is here for future-proofing and interface compliance.
        """
        if self._runner:
            logger.debug("RunnerBasedExecutor cleanup called")
            # Future: Add Runner cleanup if ADK adds it
            self._runner = None

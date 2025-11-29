"""Response builder for formatting API responses.

Wraps ResponseFormatter with a cleaner interface.
"""

from typing import Dict, Any

from ..response_formatter import ResponseFormatter
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ResponseBuilder:
    """Builds API responses from workflow results.

    High Cohesion:
    - All response formatting logic centralized
    - Single responsibility: format responses

    Low Coupling:
    - No dependency on workflow execution
    - No dependency on agents
    - Reusable across different executors

    Responsibility:
    - Format success responses
    - Format error responses
    - Ensure consistent response structure

    NOT responsible for:
    - Workflow execution
    - State management
    - Business logic
    """

    def __init__(self, model_name: str):
        """Initialize builder.

        Args:
            model_name: Model name to include in responses
        """
        self.model_name = model_name
        self._formatter = ResponseFormatter(model_name)

    def build_success_response(
        self,
        final_state: Dict[str, Any],
        session_id: str,
        timestamp: str
    ) -> Dict[str, Any]:
        """Build success response from final workflow state.

        Delegates to ResponseFormatter for backward compatibility
        while providing a cleaner interface.

        Args:
            final_state: Final session state from workflow
            session_id: Session identifier
            timestamp: Execution timestamp

        Returns:
            Formatted response dictionary with structure:
            {
                "session_id": str,
                "timestamp": str,
                "status": "approved" | "rejected",
                "plan": str,
                "risk_tags": List[str],
                "iterations": int,
                "health_analysis": Dict,
                "validation_result": Dict,
                "workflow_type": "adk",
                "model": str
            }
        """
        return self._formatter.format_success_response(
            final_state,
            session_id,
            timestamp,
            self.model_name
        )

    def build_error_response(
        self,
        error: Exception,
        session_id: str,
        timestamp: str
    ) -> Dict[str, Any]:
        """Build error response with fallback plan.

        Args:
            error: Exception that occurred
            session_id: Session identifier
            timestamp: Execution timestamp

        Returns:
            Formatted error response with safe fallback plan
        """
        return self._formatter.format_error_response(
            error,
            session_id,
            timestamp,
            self.model_name
        )

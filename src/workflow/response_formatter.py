"""Response formatting module for ADK workflow results.

Separates response formatting concerns from orchestration logic.
Extracted from orchestrator.py lines 257-400.
"""

from typing import Dict, List, Optional
from ..utils.json_parser import parse_agent_json_output
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ResponseFormatter:
    """Formats ADK workflow results into API responses.

    This class handles the transformation of raw ADK workflow outputs
    into structured response dictionaries suitable for API responses.

    Responsibilities:
    - Parse and validate workflow outputs
    - Format success responses with proper status codes
    - Generate error/fallback responses
    - Create safe generic advice when personalized plans fail
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize response formatter.

        Args:
            model_name: Model name to include in responses
        """
        self.model_name = model_name
        self.logger = logger

    def format_success_response(
        self,
        workflow_state: Dict,
        session_id: str,
        timestamp: str,
        model_name: Optional[str] = None
    ) -> Dict:
        """Format successful workflow result.

        Extracted from orchestrator.py lines 257-327 (_format_adk_output).

        Args:
            workflow_state: Final state from ADK workflow execution
            session_id: Session identifier
            timestamp: Execution timestamp
            model_name: Model name used (defaults to instance model_name)

        Returns:
            Formatted response dictionary with fields:
                - session_id: str
                - timestamp: str
                - status: str ("approved" or "rejected")
                - plan: str (markdown plan)
                - risk_tags: List[str]
                - iterations: int
                - health_analysis: Dict
                - validation_result: Dict
                - workflow_type: str ("adk")
                - model: str

        Raises:
            ValueError: If workflow_state missing required keys
        """
        model = model_name or self.model_name

        # Validate required output keys exist
        required_keys = ["health_analysis", "current_plan", "validation_result"]
        missing_keys = [k for k in required_keys if k not in workflow_state]

        if missing_keys:
            self.logger.error(
                "Incomplete workflow result",
                extra={
                    "missing_keys": missing_keys,
                    "available_keys": list(workflow_state.keys())
                }
            )
            raise ValueError(f"Workflow missing required outputs: {missing_keys}")

        # Extract and parse health analysis (handles markdown-wrapped JSON)
        health_analysis = parse_agent_json_output(
            workflow_state.get("health_analysis", {}),
            field_name="health_analysis",
            fallback_value={}
        )

        # Extract and parse validation result (handles markdown-wrapped JSON)
        validation_result = parse_agent_json_output(
            workflow_state.get("validation_result", {}),
            field_name="validation_result",
            fallback_value={}
        )

        # Extract risk_tags from parsed health_analysis
        risk_tags = health_analysis.get("risk_tags", []) if isinstance(health_analysis, dict) else []

        # Determine status based on validation decision
        status = "approved"
        if isinstance(validation_result, dict):
            decision = validation_result.get("decision", "APPROVE")
            if decision != "APPROVE":
                status = "rejected"

        # Extract iteration count from ADK loop metadata (if available)
        # ADK LoopAgent may provide this in metadata
        iterations = workflow_state.get("_loop_iterations", 1)
        if iterations == 1 and isinstance(validation_result, dict):
            # Fallback: check if there's retry information
            iterations = workflow_state.get("iterations", 1)

        return {
            "session_id": session_id,
            "timestamp": timestamp,
            "status": status,
            "plan": workflow_state.get("current_plan", ""),
            "risk_tags": risk_tags,
            "iterations": iterations,
            "health_analysis": health_analysis,
            "validation_result": validation_result,
            "workflow_type": "adk",
            "model": model,
        }

    def format_error_response(
        self,
        error: Exception,
        session_id: str,
        timestamp: str,
        model_name: Optional[str] = None
    ) -> Dict:
        """Format error/fallback response.

        Extracted from orchestrator.py lines 329-357 (_generate_fallback_from_error).

        Args:
            error: Exception that occurred
            session_id: Session identifier
            timestamp: Execution timestamp
            model_name: Model name used (defaults to instance model_name)

        Returns:
            Fallback response dictionary with fields:
                - session_id: str
                - timestamp: str
                - status: str ("fallback")
                - plan: str (safe generic advice)
                - risk_tags: List[str] (empty)
                - iterations: int (1)
                - health_analysis: Dict (empty)
                - validation_result: Dict (empty)
                - message: str
                - error: str
                - workflow_type: str ("adk")
                - model: str
        """
        model = model_name or self.model_name
        fallback_plan = self.create_safe_fallback_plan([])

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
            "error": str(error) if error else "",
            "workflow_type": "adk",
            "model": model,
        }

    def create_safe_fallback_plan(self, risk_tags: List[str]) -> str:
        """Generate safe generic advice.

        Extracted from orchestrator.py lines 359-400 (_create_safe_fallback_plan).

        Note: risk_tags parameter is currently unused but kept for future expansion
        where we might want to tailor generic advice based on identified risks.

        Args:
            risk_tags: List of identified risk tags (currently unused)

        Returns:
            Safe fallback plan in Markdown format with general health recommendations
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

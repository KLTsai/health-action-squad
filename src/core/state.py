"""SessionState dataclass for Health Action Squad.

This module defines the immutable SessionState that flows through all agents.
ALL context must be managed through this state object - no stateless parameter passing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class WorkflowStatus(Enum):
    """Workflow status enumeration - ONLY these values allowed."""
    INIT = "init"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    FAILED = "failed"


@dataclass(frozen=True)
class SessionState:
    """Immutable session state for agent workflow.

    This is the single source of truth for all workflow context.
    All agents MUST read from and write to this state.

    Attributes:
        user_profile: Fixed user data (age, gender, preferences, etc.)
        health_metrics: Parsed health report results from AnalystAgent
        risk_tags: List of identified risk flags (e.g., ["high_cholesterol", "sedentary"])
        current_plan: Generated lifestyle plan in Markdown format
        feedback_history: List of feedback dicts from each Guard iteration
        retry_count: Current Planner-Guard loop iteration counter
        status: Current workflow status (WorkflowStatus enum)
        session_id: Unique identifier for this session
        timestamp: Session creation timestamp
    """

    # Core data
    user_profile: Dict = field(default_factory=dict)
    health_metrics: Dict = field(default_factory=dict)
    risk_tags: List[str] = field(default_factory=list)

    # Planning & validation
    current_plan: str = ""
    feedback_history: List[Dict] = field(default_factory=list)
    retry_count: int = 0

    # Workflow control
    status: WorkflowStatus = WorkflowStatus.INIT
    session_id: str = ""
    timestamp: Optional[str] = None

    # Error tracking
    error_message: str = ""

    def update(self, **kwargs) -> 'SessionState':
        """Create a new SessionState with updated fields.

        Since SessionState is immutable (frozen=True), we use this method
        to create a new instance with modified fields.

        Args:
            **kwargs: Fields to update

        Returns:
            New SessionState instance with updated fields

        Example:
            new_state = state.update(status=WorkflowStatus.PLANNING, retry_count=1)
        """
        from dataclasses import replace
        return replace(self, **kwargs)

    def to_dict(self) -> Dict:
        """Convert state to dictionary for serialization.

        Returns:
            Dictionary representation of state
        """
        return {
            "user_profile": self.user_profile,
            "health_metrics": self.health_metrics,
            "risk_tags": self.risk_tags,
            "current_plan": self.current_plan,
            "feedback_history": self.feedback_history,
            "retry_count": self.retry_count,
            "status": self.status.value,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionState':
        """Create SessionState from dictionary.

        Args:
            data: Dictionary with state data

        Returns:
            New SessionState instance
        """
        # Convert status string to enum
        if "status" in data and isinstance(data["status"], str):
            data["status"] = WorkflowStatus(data["status"])
        return cls(**data)


# Maximum retry attempts for Planner-Guard loop
MAX_RETRIES = 3

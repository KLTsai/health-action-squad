"""Unit tests for SessionState and domain models."""

import pytest
from dataclasses import FrozenInstanceError

from src.domain.state import SessionState, WorkflowStatus, MAX_RETRIES


class TestSessionState:
    """Test suite for SessionState."""

    def test_session_state_is_immutable(self):
        """Test that SessionState is frozen (immutable)."""
        state = SessionState(
            user_profile={"age": 30},
            health_metrics={},
            risk_tags=[],
            current_plan="",
            feedback_history=[],
            retry_count=0,
            status=WorkflowStatus.INIT
        )

        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            state.retry_count = 1

    def test_session_state_update_creates_new_instance(self):
        """Test that SessionState.update() creates a new instance."""
        state = SessionState(
            user_profile={"age": 30},
            health_metrics={},
            risk_tags=[],
            current_plan="",
            feedback_history=[],
            retry_count=0,
            status=WorkflowStatus.INIT
        )

        new_state = state.update(retry_count=1, status=WorkflowStatus.PLANNING)

        # Original state should be unchanged
        assert state.retry_count == 0
        assert state.status == WorkflowStatus.INIT

        # New state should have updated values
        assert new_state.retry_count == 1
        assert new_state.status == WorkflowStatus.PLANNING

        # They should be different objects
        assert state is not new_state

    def test_session_state_defaults(self):
        """Test SessionState default values."""
        state = SessionState()

        assert state.user_profile == {}
        assert state.health_metrics == {}
        assert state.risk_tags == []
        assert state.current_plan == ""
        assert state.feedback_history == []
        assert state.retry_count == 0
        assert state.status == WorkflowStatus.INIT

    def test_session_state_with_custom_values(self):
        """Test SessionState with custom values."""
        user_profile = {"age": 45, "gender": "male"}
        health_metrics = {"cholesterol": 220}
        risk_tags = ["high_cholesterol"]
        current_plan = "# Health Plan"
        feedback_history = [{"iteration": 1, "feedback": "Test"}]
        retry_count = 2
        status = WorkflowStatus.APPROVED

        state = SessionState(
            user_profile=user_profile,
            health_metrics=health_metrics,
            risk_tags=risk_tags,
            current_plan=current_plan,
            feedback_history=feedback_history,
            retry_count=retry_count,
            status=status
        )

        assert state.user_profile == user_profile
        assert state.health_metrics == health_metrics
        assert state.risk_tags == risk_tags
        assert state.current_plan == current_plan
        assert state.feedback_history == feedback_history
        assert state.retry_count == retry_count
        assert state.status == status


class TestWorkflowStatus:
    """Test suite for WorkflowStatus enum."""

    def test_workflow_status_enum_values(self):
        """Test that WorkflowStatus has all required values."""
        expected_statuses = ["INIT", "ANALYZING", "PLANNING", "REVIEWING", "APPROVED", "FAILED"]

        for status_name in expected_statuses:
            assert hasattr(WorkflowStatus, status_name)

    def test_workflow_status_enum_types(self):
        """Test that WorkflowStatus is an Enum."""
        from enum import Enum
        assert isinstance(WorkflowStatus.INIT, WorkflowStatus)
        assert isinstance(WorkflowStatus.APPROVED, WorkflowStatus)
        assert isinstance(WorkflowStatus.FAILED, WorkflowStatus)
        # Values should be strings
        assert isinstance(WorkflowStatus.INIT.value, str)
        assert isinstance(WorkflowStatus.APPROVED.value, str)


class TestConstants:
    """Test suite for module constants."""

    def test_max_retries_constant(self):
        """Test that MAX_RETRIES is defined and has expected value."""
        assert MAX_RETRIES is not None
        assert isinstance(MAX_RETRIES, int)
        assert MAX_RETRIES == 3  # As per CLAUDE.md specification

"""Unit tests for Orchestrator with clean architecture."""

import pytest
from google.adk.agents import SequentialAgent, LoopAgent, LlmAgent
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from src.workflow.orchestrator import Orchestrator
from src.workflow.executors.base import WorkflowExecutor
from src.domain.state import MAX_RETRIES


class TestOrchestratorInitialization:
    """Test suite for Orchestrator initialization."""

    @patch('src.workflow.orchestrator.AgentFactory')
    def test_orchestrator_initialization_with_defaults(self, mock_factory):
        """Test that Orchestrator initializes with default parameters."""
        # Setup mock workflow
        mock_workflow = MagicMock(spec=SequentialAgent)
        mock_factory.create_workflow.return_value = mock_workflow

        orchestrator = Orchestrator()

        assert orchestrator is not None
        assert orchestrator.model_name == "gemini-2.5-flash"
        assert orchestrator.executor is not None
        assert orchestrator.workflow is mock_workflow
        assert orchestrator.response_builder is not None
        
        # Verify factory was called
        mock_factory.create_workflow.assert_called_once_with("gemini-2.5-flash")

    @patch('src.workflow.orchestrator.AgentFactory')
    def test_orchestrator_initialization_with_custom_model(self, mock_factory):
        """Test that Orchestrator initializes with custom model name."""
        orchestrator = Orchestrator(model_name="gemini-1.5-pro")

        assert orchestrator.model_name == "gemini-1.5-pro"
        mock_factory.create_workflow.assert_called_once_with("gemini-1.5-pro")

    @patch('src.workflow.orchestrator.AgentFactory')
    def test_orchestrator_has_workflow_executor(self, mock_factory):
        """Test that Orchestrator has a WorkflowExecutor instance."""
        orchestrator = Orchestrator()

        assert hasattr(orchestrator, 'executor')
        assert orchestrator.executor is not None

    @patch('src.workflow.orchestrator.AgentFactory')
    def test_orchestrator_has_response_builder(self, mock_factory):
        """Test that Orchestrator has a ResponseBuilder instance."""
        orchestrator = Orchestrator()

        assert hasattr(orchestrator, 'response_builder')
        assert orchestrator.response_builder is not None

    @patch('src.workflow.orchestrator.AgentFactory')
    def test_orchestrator_creates_workflow_via_factory(self, mock_factory):
        """Test that Orchestrator creates workflow using AgentFactory."""
        mock_workflow = MagicMock(spec=SequentialAgent)
        mock_factory.create_workflow.return_value = mock_workflow
        
        orchestrator = Orchestrator(model_name="gemini-2.5-flash")

        # Workflow should be created by factory
        assert orchestrator.workflow is mock_workflow

    @patch('src.workflow.orchestrator.AgentFactory')
    def test_orchestrator_with_custom_executor(self, mock_factory):
        """Test that Orchestrator accepts custom executor via dependency injection."""
        mock_executor = Mock(spec=WorkflowExecutor)
        orchestrator = Orchestrator(executor=mock_executor)

        assert orchestrator.executor is mock_executor


class TestOrchestratorWorkflowStructure:
    """Test suite for verifying workflow structure.
    
    Note: Since we mock AgentFactory, we are testing that Orchestrator correctly
    uses the workflow returned by the factory. The actual structure of the workflow
    is tested in test_agent_factory.py (if it existed) or implicitly via integration tests.
    Here we verify Orchestrator's interaction with the workflow object.
    """

    @patch('src.workflow.orchestrator.AgentFactory')
    def test_workflow_is_stored(self, mock_factory):
        """Test that workflow returned by factory is stored."""
        mock_workflow = MagicMock(spec=SequentialAgent)
        mock_workflow.name = "HealthActionSquad"
        mock_factory.create_workflow.return_value = mock_workflow
        
        orchestrator = Orchestrator()

        assert orchestrator.workflow is mock_workflow
        assert orchestrator.workflow.name == "HealthActionSquad"


class TestOrchestratorExecute:
    """Test suite for execute method."""

    @patch('src.workflow.orchestrator.AgentFactory')
    def test_execute_is_async(self, mock_factory):
        """Test that execute method is async."""
        orchestrator = Orchestrator()

        import inspect
        assert inspect.iscoroutinefunction(orchestrator.execute)

    @pytest.mark.asyncio
    @patch('src.workflow.orchestrator.AgentFactory')
    async def test_execute_with_mocked_executor(self, mock_factory):
        """Test execute method with mocked executor."""
        # Create mock executor
        mock_executor = Mock(spec=WorkflowExecutor)
        mock_executor.execute = AsyncMock(return_value={
            "health_analysis": '{"risk_tags": ["high_cholesterol"], "health_metrics": {}}',
            "current_plan": "# Test Plan",
            "validation_result": '{"decision": "APPROVE"}'
        })

        orchestrator = Orchestrator(executor=mock_executor)

        # Execute
        result = await orchestrator.execute(
            health_report={"cholesterol": 240},
            user_profile={"age": 45}
        )

        # Verify executor was called
        assert mock_executor.execute.called
        # Verify result structure
        assert "session_id" in result
        assert "status" in result
        assert "plan" in result

    @pytest.mark.asyncio
    @patch('src.workflow.orchestrator.AgentFactory')
    async def test_execute_passes_health_report_and_profile(self, mock_factory, sample_health_report, sample_user_profile):
        """Test that execute passes health_report and user_profile to executor."""
        mock_executor = Mock(spec=WorkflowExecutor)
        mock_executor.execute = AsyncMock(return_value={
            "health_analysis": '{"risk_tags": [], "health_metrics": {}}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        })

        orchestrator = Orchestrator(executor=mock_executor)
        await orchestrator.execute(
            health_report=sample_health_report,
            user_profile=sample_user_profile
        )

        # Verify executor.execute was called with initial_state containing both
        call_args = mock_executor.execute.call_args
        assert call_args is not None
        kwargs = call_args.kwargs
        assert "initial_state" in kwargs
        assert "health_report" in kwargs["initial_state"]
        assert "user_profile" in kwargs["initial_state"]

    @pytest.mark.asyncio
    @patch('src.workflow.orchestrator.AgentFactory')
    async def test_execute_handles_errors_gracefully(self, mock_factory):
        """Test that execute handles errors and returns error response."""
        mock_executor = Mock(spec=WorkflowExecutor)
        mock_executor.execute = AsyncMock(side_effect=ValueError("Test error"))

        orchestrator = Orchestrator(executor=mock_executor)
        result = await orchestrator.execute(health_report={})

        # Should return error response
        assert result["status"] == "fallback"
        assert "error" in result
        assert "Test error" in result["error"]


class TestOrchestratorCleanup:
    """Test suite for cleanup method."""

    @patch('src.workflow.orchestrator.AgentFactory')
    def test_cleanup_is_async(self, mock_factory):
        """Test that cleanup method is async."""
        orchestrator = Orchestrator()

        import inspect
        assert inspect.iscoroutinefunction(orchestrator.cleanup)

    @pytest.mark.asyncio
    @patch('src.workflow.orchestrator.AgentFactory')
    async def test_cleanup_delegates_to_executor(self, mock_factory):
        """Test that cleanup calls executor.cleanup()."""
        mock_executor = Mock(spec=WorkflowExecutor)
        mock_executor.cleanup = AsyncMock()

        orchestrator = Orchestrator(executor=mock_executor)
        await orchestrator.cleanup()

        # Verify executor cleanup was called
        assert mock_executor.cleanup.called

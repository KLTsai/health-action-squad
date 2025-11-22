"""Unit tests for Orchestrator."""

import pytest
from google.adk.agents import SequentialAgent, LoopAgent, LlmAgent
from unittest.mock import AsyncMock, patch

from src.workflow.orchestrator import Orchestrator
from src.domain.state import MAX_RETRIES


class TestOrchestrator:
    """Test suite for Orchestrator."""

    def test_orchestrator_initialization(self):
        """Test that Orchestrator initializes correctly."""
        orchestrator = Orchestrator(model_name="gemini-2.5-flash")

        assert orchestrator is not None
        assert orchestrator.model_name == "gemini-2.5-flash"

    def test_orchestrator_creates_all_agents(self):
        """Test that Orchestrator creates all three agents."""
        orchestrator = Orchestrator(model_name="gemini-2.5-flash")

        assert orchestrator.analyst_agent is not None
        assert orchestrator.planner_agent is not None
        assert orchestrator.guard_agent is not None

        # All agents should be LlmAgent instances
        assert isinstance(orchestrator.analyst_agent, LlmAgent)
        assert isinstance(orchestrator.planner_agent, LlmAgent)
        assert isinstance(orchestrator.guard_agent, LlmAgent)

    def test_orchestrator_creates_planning_loop(self):
        """Test that Orchestrator creates LoopAgent for Planner-Guard loop."""
        orchestrator = Orchestrator(model_name="gemini-2.5-flash")

        assert orchestrator.planning_loop is not None
        assert isinstance(orchestrator.planning_loop, LoopAgent)

    def test_planning_loop_has_correct_max_iterations(self):
        """Test that planning loop has max_iterations set to MAX_RETRIES."""
        orchestrator = Orchestrator(model_name="gemini-2.5-flash")

        # LoopAgent should have max_iterations attribute
        assert hasattr(orchestrator.planning_loop, 'max_iterations')
        assert orchestrator.planning_loop.max_iterations == MAX_RETRIES

    def test_orchestrator_creates_main_workflow(self):
        """Test that Orchestrator creates SequentialAgent workflow."""
        orchestrator = Orchestrator(model_name="gemini-2.5-flash")

        assert orchestrator.workflow is not None
        assert isinstance(orchestrator.workflow, SequentialAgent)

    def test_workflow_structure(self):
        """Test that workflow has correct structure (Analyst → PlanningLoop)."""
        orchestrator = Orchestrator(model_name="gemini-2.5-flash")

        # Workflow should have sub_agents
        assert hasattr(orchestrator.workflow, 'sub_agents')
        assert orchestrator.workflow.sub_agents is not None
        assert len(orchestrator.workflow.sub_agents) == 2

        # First should be analyst, second should be planning loop
        assert orchestrator.workflow.sub_agents[0] == orchestrator.analyst_agent
        assert orchestrator.workflow.sub_agents[1] == orchestrator.planning_loop

    def test_execute_is_async(self):
        """Test that execute method is async."""
        orchestrator = Orchestrator(model_name="gemini-2.5-flash")

        import inspect
        assert inspect.iscoroutinefunction(orchestrator.execute)

    # Note: ADK workflow.run() integration tests require valid API key
    # These tests would be in tests/e2e/ with actual API calls
    # Unit tests focus on workflow structure and configuration

    def test_orchestrator_with_different_models(self):
        """Test that Orchestrator works with different model names."""
        models = ["gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash"]

        for model_name in models:
            orchestrator = Orchestrator(model_name=model_name)
            assert orchestrator.model_name == model_name
            assert orchestrator.analyst_agent.model == model_name
            assert orchestrator.planner_agent.model == model_name
            assert orchestrator.guard_agent.model == model_name

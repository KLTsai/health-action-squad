"""Unit tests for LifestylePlannerAgent."""

import pytest
from google.adk.agents import LlmAgent

from src.agents.planner_agent import LifestylePlannerAgent


class TestLifestylePlannerAgent:
    """Test suite for LifestylePlannerAgent."""

    def test_create_agent_returns_llm_agent(self):
        """Test that create_agent returns an LlmAgent instance."""
        agent = LifestylePlannerAgent.create_agent(model_name="gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent is not None

    def test_agent_has_correct_name(self):
        """Test that agent has correct name."""
        agent = LifestylePlannerAgent.create_agent(model_name="gemini-2.5-flash")

        assert agent.name == "LifestylePlanner"

    def test_agent_has_correct_output_key(self):
        """Test that agent has correct output_key."""
        agent = LifestylePlannerAgent.create_agent(model_name="gemini-2.5-flash")

        assert agent.output_key == "current_plan"

    def test_agent_has_description(self):
        """Test that agent has description."""
        agent = LifestylePlannerAgent.create_agent(model_name="gemini-2.5-flash")

        assert agent.description is not None
        assert len(agent.description) > 0

    def test_agent_instruction_has_state_placeholders(self):
        """Test that agent instruction contains ADK state injection placeholders."""
        agent = LifestylePlannerAgent.create_agent(model_name="gemini-2.5-flash")

        instruction = agent.instruction
        # Check for ADK placeholder syntax
        assert "{health_analysis}" in instruction
        assert "{user_profile}" in instruction

    def test_agent_instruction_mentions_validation_result(self):
        """Test that agent instruction mentions validation_result for retry logic."""
        agent = LifestylePlannerAgent.create_agent(model_name="gemini-2.5-flash")

        instruction = agent.instruction
        # Should handle feedback from SafetyGuard on retry
        assert "{validation_result}" in instruction

    def test_agent_uses_specified_model(self):
        """Test that agent uses specified model name."""
        model_name = "gemini-2.5-pro"
        agent = LifestylePlannerAgent.create_agent(model_name=model_name)

        assert agent.model == model_name

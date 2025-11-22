"""Unit tests for ReportAnalystAgent."""

import pytest
from google.adk.agents import LlmAgent

from src.agents.analyst_agent import ReportAnalystAgent


class TestReportAnalystAgent:
    """Test suite for ReportAnalystAgent."""

    def test_create_agent_returns_llm_agent(self):
        """Test that create_agent returns an LlmAgent instance."""
        agent = ReportAnalystAgent.create_agent(model_name="gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent is not None

    def test_agent_has_correct_name(self):
        """Test that agent has correct name."""
        agent = ReportAnalystAgent.create_agent(model_name="gemini-2.5-flash")

        assert agent.name == "ReportAnalyst"

    def test_agent_has_correct_output_key(self):
        """Test that agent has correct output_key."""
        agent = ReportAnalystAgent.create_agent(model_name="gemini-2.5-flash")

        assert agent.output_key == "health_analysis"

    def test_agent_has_description(self):
        """Test that agent has description."""
        agent = ReportAnalystAgent.create_agent(model_name="gemini-2.5-flash")

        assert agent.description is not None
        assert len(agent.description) > 0
        assert "health reports" in agent.description.lower() or "metrics" in agent.description.lower()

    def test_agent_uses_specified_model(self):
        """Test that agent uses specified model name."""
        model_name = "gemini-2.5-flash"
        agent = ReportAnalystAgent.create_agent(model_name=model_name)

        assert agent.model == model_name

    def test_agent_has_instruction(self):
        """Test that agent has instruction/prompt."""
        agent = ReportAnalystAgent.create_agent(model_name="gemini-2.5-flash")

        assert agent.instruction is not None
        assert len(agent.instruction) > 0

    def test_agent_instruction_contains_output_format(self):
        """Test that agent instruction contains output format specification."""
        agent = ReportAnalystAgent.create_agent(model_name="gemini-2.5-flash")

        instruction_lower = agent.instruction.lower()
        assert "health_metrics" in instruction_lower or "risk_tags" in instruction_lower
        assert "json" in instruction_lower

    def test_create_agent_with_different_models(self):
        """Test that create_agent works with different model names."""
        models = ["gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash"]

        for model_name in models:
            agent = ReportAnalystAgent.create_agent(model_name=model_name)
            assert agent.model == model_name
            assert isinstance(agent, LlmAgent)

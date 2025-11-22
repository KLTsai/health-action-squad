"""Unit tests for SafetyGuardAgent."""

import pytest
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from src.agents.guard_agent import SafetyGuardAgent


class TestSafetyGuardAgent:
    """Test suite for SafetyGuardAgent."""

    def test_create_agent_returns_llm_agent(self):
        """Test that create_agent returns an LlmAgent instance."""
        agent = SafetyGuardAgent.create_agent(model_name="gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent is not None

    def test_agent_has_correct_name(self):
        """Test that agent has correct name."""
        agent = SafetyGuardAgent.create_agent(model_name="gemini-2.5-flash")

        assert agent.name == "SafetyGuard"

    def test_agent_has_correct_output_key(self):
        """Test that agent has correct output_key."""
        agent = SafetyGuardAgent.create_agent(model_name="gemini-2.5-flash")

        assert agent.output_key == "validation_result"

    def test_agent_has_exit_loop_tool(self):
        """Test that agent has exit_loop tool for loop termination."""
        agent = SafetyGuardAgent.create_agent(model_name="gemini-2.5-flash")

        assert hasattr(agent, 'tools')
        assert agent.tools is not None
        assert len(agent.tools) > 0

        # Check that at least one tool is a FunctionTool
        has_function_tool = any(isinstance(tool, FunctionTool) for tool in agent.tools)
        assert has_function_tool

    def test_agent_instruction_mentions_exit_loop(self):
        """Test that agent instruction mentions exit_loop tool usage."""
        agent = SafetyGuardAgent.create_agent(model_name="gemini-2.5-flash")

        instruction_lower = agent.instruction.lower()
        assert "exit_loop" in instruction_lower or "exit" in instruction_lower

    def test_agent_instruction_contains_safety_rules(self):
        """Test that agent instruction contains safety rules from YAML."""
        agent = SafetyGuardAgent.create_agent(model_name="gemini-2.5-flash")

        instruction_lower = agent.instruction.lower()
        # Should contain some safety-related keywords
        assert any(keyword in instruction_lower for keyword in [
            "safety", "risk", "prohibited", "violation", "approve", "reject"
        ])

    def test_load_safety_rules(self):
        """Test that _load_safety_rules loads the YAML file."""
        safety_rules = SafetyGuardAgent._load_safety_rules()

        assert safety_rules is not None
        assert isinstance(safety_rules, dict)
        # Should have some safety rules defined
        assert len(safety_rules) > 0

    def test_agent_instruction_has_decision_format(self):
        """Test that agent instruction specifies decision format."""
        agent = SafetyGuardAgent.create_agent(model_name="gemini-2.5-flash")

        instruction_lower = agent.instruction.lower()
        assert "approve" in instruction_lower
        assert "reject" in instruction_lower

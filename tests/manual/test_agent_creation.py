"""Test script to verify ADK agent creation.

Tests that all three refactored agents can be instantiated correctly.
"""

import sys
from pathlib import Path

# Add project root to path (supports both pytest and direct python execution)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.agents.analyst_agent import ReportAnalystAgent
from src.agents.planner_agent import LifestylePlannerAgent
from src.agents.guard_agent import SafetyGuardAgent
from google.adk.agents import LlmAgent


def test_analyst_agent():
    """Test ReportAnalystAgent creation."""
    print("Testing ReportAnalystAgent...")
    agent = ReportAnalystAgent.create_agent(model_name="gemini-2.5-flash")

    assert isinstance(agent, LlmAgent), "Agent should be LlmAgent instance"
    assert agent.name == "ReportAnalyst", f"Expected name 'ReportAnalyst', got {agent.name}"
    assert agent.output_key == "health_analysis", f"Expected output_key 'health_analysis', got {agent.output_key}"

    print("[OK] ReportAnalystAgent created successfully")
    print(f"   - Name: {agent.name}")
    print(f"   - Output key: {agent.output_key}")
    print(f"   - Model: {agent.model}")
    return agent


def test_planner_agent():
    """Test LifestylePlannerAgent creation."""
    print("\nTesting LifestylePlannerAgent...")
    agent = LifestylePlannerAgent.create_agent(model_name="gemini-2.5-flash")

    assert isinstance(agent, LlmAgent), "Agent should be LlmAgent instance"
    assert agent.name == "LifestylePlanner", f"Expected name 'LifestylePlanner', got {agent.name}"
    assert agent.output_key == "current_plan", f"Expected output_key 'current_plan', got {agent.output_key}"

    print("[OK] LifestylePlannerAgent created successfully")
    print(f"   - Name: {agent.name}")
    print(f"   - Output key: {agent.output_key}")
    print(f"   - Model: {agent.model}")
    return agent


def test_guard_agent():
    """Test SafetyGuardAgent creation."""
    print("\nTesting SafetyGuardAgent...")
    agent = SafetyGuardAgent.create_agent(model_name="gemini-2.5-flash")

    assert isinstance(agent, LlmAgent), "Agent should be LlmAgent instance"
    assert agent.name == "SafetyGuard", f"Expected name 'SafetyGuard', got {agent.name}"
    assert agent.output_key == "validation_result", f"Expected output_key 'validation_result', got {agent.output_key}"
    assert hasattr(agent, 'tools') and len(agent.tools) > 0, "Guard agent should have tools"

    print("[OK] SafetyGuardAgent created successfully")
    print(f"   - Name: {agent.name}")
    print(f"   - Output key: {agent.output_key}")
    print(f"   - Model: {agent.model}")
    print(f"   - Tools: {[tool.name if hasattr(tool, 'name') else str(type(tool).__name__) for tool in agent.tools]}")
    return agent


def main():
    """Run all agent creation tests."""
    print("=" * 60)
    print("ADK Agent Creation Tests")
    print("=" * 60)

    try:
        analyst = test_analyst_agent()
        planner = test_planner_agent()
        guard = test_guard_agent()

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL TESTS PASSED")
        print("=" * 60)
        print("\nAll three agents successfully created:")
        print(f"  1. {analyst.name} -> {analyst.output_key}")
        print(f"  2. {planner.name} -> {planner.output_key}")
        print(f"  3. {guard.name} -> {guard.output_key}")

        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print("[FAILED] TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

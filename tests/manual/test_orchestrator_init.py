"""Test script to verify ADK Orchestrator initialization.

Tests that the Orchestrator can be created with ADK workflow agents.
"""

import sys
from pathlib import Path

# Add project root to path (supports both pytest and direct python execution)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.workflow.orchestrator import Orchestrator
from google.adk.agents import SequentialAgent, LoopAgent


def test_orchestrator_init():
    """Test Orchestrator initialization."""
    print("=" * 60)
    print("ADK Orchestrator Initialization Test")
    print("=" * 60)

    print("\nInitializing Orchestrator...")
    orchestrator = Orchestrator(model_name="gemini-2.5-flash")

    print("[OK] Orchestrator created successfully")
    print(f"   - Model: {orchestrator.model_name}")
    print(f"   - Workflow type: {type(orchestrator.workflow).__name__}")
    print(f"   - Planning loop type: {type(orchestrator.planning_loop).__name__}")

    # Verify workflow structure
    assert isinstance(orchestrator.workflow, SequentialAgent), \
        "Workflow should be SequentialAgent"
    assert isinstance(orchestrator.planning_loop, LoopAgent), \
        "Planning loop should be LoopAgent"

    print("\n[OK] Workflow structure verified:")
    print(f"   - SequentialAgent: {orchestrator.workflow.name}")
    print(f"   - LoopAgent: {orchestrator.planning_loop.name}")
    print(f"   - Loop max iterations: {orchestrator.planning_loop.max_iterations}")

    print("\n[OK] Agent composition verified:")
    print(f"   - Analyst: {orchestrator.analyst_agent.name}")
    print(f"   - Planner: {orchestrator.planner_agent.name}")
    print(f"   - Guard: {orchestrator.guard_agent.name}")
    print(f"   - Guard tools: {[t.name for t in orchestrator.guard_agent.tools]}")

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS PASSED")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(test_orchestrator_init())
    except Exception as e:
        print("\n" + "=" * 60)
        print("[FAILED] TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

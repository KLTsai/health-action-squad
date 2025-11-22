"""Test script to verify ADK workflow structure and data flow.

This test validates the workflow structure without requiring actual LLM calls.
It checks data loading, state preparation, and workflow composition.
"""

import sys
import json
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from src.workflow.orchestrator import Orchestrator


def load_sample_data():
    """Load sample health report and user profile."""
    health_report_path = project_root / "resources" / "data" / "sample_health_report.json"
    user_profile_path = project_root / "resources" / "data" / "sample_user_profile.json"

    with open(health_report_path, "r", encoding="utf-8") as f:
        health_report = json.load(f)

    with open(user_profile_path, "r", encoding="utf-8") as f:
        user_profile = json.load(f)

    return health_report, user_profile


def test_workflow_structure():
    """Test workflow structure and composition."""
    print("=" * 60)
    print("ADK Workflow Structure Test")
    print("=" * 60)

    # Initialize orchestrator
    print("\n[1/5] Initializing Orchestrator...")
    orchestrator = Orchestrator(model_name="gemini-pro")
    print("    [OK] Orchestrator initialized")

    # Verify workflow structure
    print("\n[2/5] Verifying workflow structure...")
    assert orchestrator.workflow is not None, "Workflow should be initialized"
    assert orchestrator.workflow.name == "HealthActionSquad", "Workflow name mismatch"
    assert len(orchestrator.workflow.sub_agents) == 2, "Should have 2 sub-agents (Analyst + Loop)"
    print("    [OK] SequentialAgent structure verified")

    # Verify loop structure
    print("\n[3/5] Verifying LoopAgent structure...")
    assert orchestrator.planning_loop is not None, "Planning loop should be initialized"
    assert orchestrator.planning_loop.name == "PlanningLoop", "Loop name mismatch"
    assert orchestrator.planning_loop.max_iterations == 3, "Max iterations should be 3"
    assert len(orchestrator.planning_loop.sub_agents) == 2, "Loop should have 2 sub-agents (Planner + Guard)"
    print("    [OK] LoopAgent structure verified")

    # Load sample data
    print("\n[4/5] Loading sample data...")
    health_report, user_profile = load_sample_data()
    print("    [OK] Sample data loaded")
    print(f"        - Health report: {len(health_report)} sections")
    print(f"        - User profile: {len(user_profile)} sections")

    # Verify data structure
    print("\n[5/5] Verifying data structure...")
    assert "patient_info" in health_report, "Health report should have patient_info"
    assert "vital_signs" in health_report, "Health report should have vital_signs"
    assert "demographics" in user_profile, "User profile should have demographics"
    assert "fitness_profile" in user_profile, "User profile should have fitness_profile"
    print("    [OK] Data structure verified")

    # Display workflow composition
    print("\n" + "=" * 60)
    print("Workflow Composition Summary")
    print("=" * 60)
    print(f"\nMain Workflow: {orchestrator.workflow.name}")
    print(f"  Type: SequentialAgent")
    print(f"  Sub-agents: {len(orchestrator.workflow.sub_agents)}")
    print(f"\n  1. {orchestrator.analyst_agent.name} (LlmAgent)")
    print(f"     Output key: {orchestrator.analyst_agent.output_key}")
    print(f"\n  2. {orchestrator.planning_loop.name} (LoopAgent)")
    print(f"     Max iterations: {orchestrator.planning_loop.max_iterations}")
    print(f"     Sub-agents:")
    print(f"       a. {orchestrator.planner_agent.name} (LlmAgent)")
    print(f"          Output key: {orchestrator.planner_agent.output_key}")
    print(f"       b. {orchestrator.guard_agent.name} (LlmAgent)")
    print(f"          Output key: {orchestrator.guard_agent.output_key}")
    print(f"          Tools: {[t.name for t in orchestrator.guard_agent.tools]}")

    # Display sample data info
    print(f"\nSample Data:")
    print(f"  Patient: {health_report['patient_info']['age']}yo {health_report['patient_info']['gender']}")
    print(f"  BMI: {health_report['vital_signs']['bmi']}")
    print(f"  Activity: {health_report['lifestyle_factors']['physical_activity']}")
    print(f"  Goals: {', '.join(user_profile['health_goals']['primary_goals'])}")

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL STRUCTURE TESTS PASSED")
    print("=" * 60)
    print("\nNote: This test validates workflow structure only.")
    print("End-to-end execution requires Gemini API key and network access.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(test_workflow_structure())
    except Exception as e:
        print("\n" + "=" * 60)
        print("[FAILED] TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

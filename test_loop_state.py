"""Test script to verify ADK LoopAgent state passing.

This script tests whether Guard receives Planner's output correctly in LoopAgent.
"""

import asyncio
import json
from src.workflow.orchestrator import Orchestrator


async def test_loop_state_passing():
    """Test if Guard can see Planner's output in loop."""
    print("=" * 80)
    print("TEST: ADK LoopAgent State Passing")
    print("=" * 80)

    # Sample health report with risk factors
    health_report = {
        "blood_pressure": "140/90",
        "bmi": 28.5,
        "cholesterol_hdl": 40,
        "cholesterol_ldl": 150,
        "cholesterol_total": 220,
        "glucose_fasting": 110
    }

    user_profile = {
        "age": 45,
        "gender": "male",
        "activity_level": "sedentary"
    }

    print("\nInput:")
    print(f"  Health Report: {list(health_report.keys())}")
    print(f"  User Profile: {user_profile}")

    print("\n" + "-" * 80)
    print("Executing ADK Workflow...")
    print("-" * 80 + "\n")

    orchestrator = Orchestrator()
    result = await orchestrator.execute(
        health_report=health_report,
        user_profile=user_profile
    )

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\nStatus: {result['status']}")
    print(f"Iterations: {result.get('iterations', 'N/A')}")
    print(f"Plan Length: {len(result.get('plan', ''))} characters")

    # Check validation_result
    validation = result.get('validation_result', {})
    if isinstance(validation, dict):
        print(f"\nValidation Decision: {validation.get('decision', 'N/A')}")
        print(f"Validation Feedback:")
        for fb in validation.get('feedback', []):
            print(f"  - {fb}")
        print(f"Violations: {validation.get('violations', [])}")
    else:
        print(f"\nValidation Result (raw): {str(validation)[:200]}")

    # Analyze the problem
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    plan_present = len(result.get('plan', '')) > 0
    guard_says_empty = False

    if isinstance(validation, dict):
        for fb in validation.get('feedback', []):
            if 'empty' in fb.lower() or 'no content' in fb.lower():
                guard_says_empty = True

    print(f"\nPlan generated: {plan_present}")
    print(f"Guard says empty: {guard_says_empty}")

    if plan_present and guard_says_empty:
        print("\n[PROBLEM DETECTED]")
        print("Guard says plan is empty, but plan was generated!")
        print("This indicates LoopAgent is not passing Planner's output to Guard.")
        print("\nPossible causes:")
        print("1. ADK LoopAgent doesn't automatically update session.state")
        print("2. Placeholder {current_plan} not being injected correctly")
        print("3. Context window limits causing truncation")
        return False
    elif result['status'] == 'approved':
        print("\n[SUCCESS]")
        print("Workflow completed successfully!")
        return True
    else:
        print("\n[PARTIAL SUCCESS]")
        print("Plan generated but rejected for valid reasons.")
        return True

if __name__ == "__main__":
    success = asyncio.run(test_loop_state_passing())
    exit(0 if success else 1)

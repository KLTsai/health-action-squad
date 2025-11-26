"""Quick test script to verify orchestrator workflow fix.

This script tests the InMemoryRunner implementation with sample health data.
"""

import asyncio
import json
import os

# Ensure API key is set before importing ADK modules
from dotenv import load_dotenv
load_dotenv()
if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

from src.workflow.orchestrator import Orchestrator


async def test_workflow_fix():
    """Test workflow with sample health data from images."""

    # Sample health report based on the uploaded images
    health_report = {
        # Physical examination from first image
        "blood_pressure_systolic": 112,
        "blood_pressure_diastolic": 68,
        "height_cm": 177.3,
        "weight_kg": 59.1,
        "bmi": 18.7,
        "heart_rate": 85,
        "waist_cm": 73,

        # Blood test results from second image
        "wbc": 4.73,
        "rbc": 4.48,
        "hemoglobin": 14.4,
        "hematocrit": 40.2,
        "platelet": 257,

        # Glucose metabolism
        "fasting_glucose": 98,
        "hba1c": 5.4,
    }

    user_profile = {
        "age": 30,
        "gender": "male"
    }

    print("=" * 80)
    print("WORKFLOW FIX TEST - ADK InMemoryRunner Implementation")
    print("=" * 80)
    print(f"\nHealth Report:")
    print(json.dumps(health_report, indent=2))
    print(f"\nUser Profile:")
    print(json.dumps(user_profile, indent=2))
    print("\n" + "=" * 80)
    print("Executing workflow...")
    print("=" * 80 + "\n")

    # Create orchestrator and execute
    orchestrator = Orchestrator()

    try:
        result = await orchestrator.execute(
            health_report=health_report,
            user_profile=user_profile
        )

        print("\n" + "=" * 80)
        print("WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)

        print(f"\nStatus: {result['status']}")
        print(f"Iterations: {result.get('iterations', 'N/A')}")
        print(f"Risk Tags: {result.get('risk_tags', [])}")
        print(f"Plan Length: {len(result.get('plan', ''))} characters")
        print(f"Session ID: {result.get('session_id', 'N/A')}")

        # Check if fallback was triggered
        if result['status'] == 'fallback':
            print("\nWARNING: Workflow entered fallback mode")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Message: {result.get('message', 'No message')}")
            return False

        # Check if plan is personalized (not generic fallback)
        if "General Health Recommendations" in result.get('plan', ''):
            print("\nWARNING: Plan appears to be generic fallback, not personalized")
            return False

        print("\nPlan Preview (first 500 chars):")
        print("-" * 80)
        print(result.get('plan', '')[:500] + "...")
        print("-" * 80)

        print("\nHealth Analysis:")
        health_analysis = result.get('health_analysis', {})
        if isinstance(health_analysis, str):
            print("  (Raw string output - may need parsing)")
            print(f"  {health_analysis[:200]}...")
        else:
            print(json.dumps(health_analysis, indent=2)[:500])

        print("\nVALIDATION PASSED")
        print("=" * 80)
        return True

    except Exception as e:
        print("\n" + "=" * 80)
        print("WORKFLOW FAILED")
        print("=" * 80)
        print(f"\nException: {type(e).__name__}")
        print(f"Message: {str(e)}")

        import traceback
        print("\nTraceback:")
        print("-" * 80)
        traceback.print_exc()
        print("-" * 80)

        return False


if __name__ == "__main__":
    print("\n" + " TESTING ADK WORKFLOW FIX ".center(80, "="))
    print("Testing InMemoryRunner implementation\n")

    success = asyncio.run(test_workflow_fix())

    print("\n" + "=" * 80)
    if success:
        print("TEST RESULT: PASSED")
    else:
        print("TEST RESULT: FAILED")
    print("=" * 80 + "\n")

    exit(0 if success else 1)

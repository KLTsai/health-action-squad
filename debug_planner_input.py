"""Debug script to check what LifestylePlanner actually receives.

This script simulates the Planner's input to understand why it's not generating plans.
"""

import json

# Simulate what we think Planner receives
health_analysis = {
    "health_metrics": {
        "blood_pressure_systolic": 112,
        "blood_pressure_diastolic": 68,
        "glucose": 98,
        "hba1c": 5.4,
        "bmi": 18.7,
        "weight_kg": 59.1,
        "height_cm": 177.3,
        "heart_rate": 85
    },
    "risk_tags": []
}

user_profile = {
    "age": 30,
    "gender": "male",
    "dietary_restrictions": "string",
    "health_goal": "string",
    "exercise_barriers": "string"
}

validation_result = None

# Format as would be injected in prompt
print("=" * 80)
print("SIMULATED PLANNER INPUT")
print("=" * 80)

print("\n## Health Analysis (from ReportAnalyst)")
print(json.dumps(health_analysis, indent=2))

print("\n## User Profile")
print(json.dumps(user_profile, indent=2))

print("\n## Previous Feedback (if this is a retry)")
print(validation_result)

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

print(f"\n✓ health_analysis type: {type(health_analysis)}")
print(f"✓ health_metrics present: {'health_metrics' in health_analysis}")
print(f"✓ risk_tags: {health_analysis['risk_tags']}")
print(f"✓ user_profile type: {type(user_profile)}")
print(f"✓ age: {user_profile.get('age')}")
print(f"✓ gender: {user_profile.get('gender')}")

print("\n" + "=" * 80)
print("EXPECTED PLANNER BEHAVIOR")
print("=" * 80)

if not health_analysis["risk_tags"]:
    print("\n⚠️  ISSUE: risk_tags is EMPTY []")
    print("   This might confuse the Planner!")
    print("   Planner might think: 'No risks to address, what should I plan for?'")

print("\nPossible reasons Planner returns 'provide more info':")
print("1. Empty risk_tags → No clear direction for plan")
print("2. Placeholder injection issue → Seeing wrong format")
print("3. Prompt ambiguity → Unclear what to do with perfect health")

print("\n" + "=" * 80)

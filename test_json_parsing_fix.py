"""Test script to verify JSON parsing fix for markdown-wrapped agent outputs.

This script tests that:
1. The json_parser utility correctly unwraps markdown-formatted JSON
2. The orchestrator properly parses agent outputs into dicts
3. Pydantic validation passes with parsed dicts
"""

import asyncio
import json
from src.utils.json_parser import parse_llm_json_response, parse_agent_json_output
from src.api.models import PlanGenerationResponse


def test_markdown_unwrapping():
    """Test markdown code block unwrapping."""
    print("=" * 80)
    print("TEST 1: Markdown Unwrapping")
    print("=" * 80)

    # Test case 1: Markdown-wrapped JSON (with json tag)
    markdown_json = '''```json
{
  "health_metrics": {
    "cholesterol_total": 220,
    "cholesterol_ldl": 140
  },
  "risk_tags": ["high_cholesterol", "high_ldl"]
}
```'''

    result = parse_llm_json_response(markdown_json, expected_type=dict)
    print("\n✓ Markdown-wrapped JSON (with tag):")
    print(f"  Input preview: {markdown_json[:50]}...")
    print(f"  Output: {json.dumps(result, indent=2)}")
    assert isinstance(result, dict)
    assert result["health_metrics"]["cholesterol_total"] == 220
    assert "high_cholesterol" in result["risk_tags"]

    # Test case 2: Markdown-wrapped JSON (without json tag)
    markdown_no_tag = '''```
{
  "decision": "APPROVE",
  "feedback": ["All good"],
  "violations": []
}
```'''

    result2 = parse_llm_json_response(markdown_no_tag, expected_type=dict)
    print("\n✓ Markdown-wrapped JSON (without tag):")
    print(f"  Input preview: {markdown_no_tag[:40]}...")
    print(f"  Output: {json.dumps(result2, indent=2)}")
    assert isinstance(result2, dict)
    assert result2["decision"] == "APPROVE"

    # Test case 3: Plain JSON (no markdown)
    plain_json = '''{"decision": "REJECT", "feedback": ["Fix this"], "violations": ["error"]}'''

    result3 = parse_llm_json_response(plain_json, expected_type=dict)
    print("\n✓ Plain JSON (no markdown):")
    print(f"  Input: {plain_json}")
    print(f"  Output: {json.dumps(result3, indent=2)}")
    assert isinstance(result3, dict)
    assert result3["decision"] == "REJECT"

    print("\n" + "=" * 80)
    print("TEST 1 PASSED: All markdown unwrapping tests successful")
    print("=" * 80)


def test_agent_output_parsing():
    """Test parse_agent_json_output helper function."""
    print("\n" + "=" * 80)
    print("TEST 2: Agent Output Parsing")
    print("=" * 80)

    # Test case 1: Already a dict (passthrough)
    dict_output = {"key": "value", "number": 42}
    result = parse_agent_json_output(dict_output, field_name="test")
    print("\n✓ Dict input (passthrough):")
    print(f"  Input: {dict_output}")
    print(f"  Output: {result}")
    assert result == dict_output

    # Test case 2: JSON string
    json_string = '{"health_metrics": {"bmi": 27.8}, "risk_tags": ["overweight"]}'
    result2 = parse_agent_json_output(json_string, field_name="health_analysis")
    print("\n✓ JSON string input:")
    print(f"  Input: {json_string}")
    print(f"  Output: {json.dumps(result2, indent=2)}")
    assert isinstance(result2, dict)
    assert result2["health_metrics"]["bmi"] == 27.8

    # Test case 3: Markdown-wrapped JSON
    markdown_output = '''```json
{
  "decision": "APPROVE",
  "feedback": ["Good to go"],
  "violations": []
}
```'''
    result3 = parse_agent_json_output(markdown_output, field_name="validation_result")
    print("\n✓ Markdown-wrapped JSON:")
    print(f"  Input preview: {markdown_output[:40]}...")
    print(f"  Output: {json.dumps(result3, indent=2)}")
    assert isinstance(result3, dict)
    assert result3["decision"] == "APPROVE"

    print("\n" + "=" * 80)
    print("TEST 2 PASSED: All agent output parsing tests successful")
    print("=" * 80)


def test_pydantic_validation():
    """Test that Pydantic models accept parsed dicts."""
    print("\n" + "=" * 80)
    print("TEST 3: Pydantic Validation")
    print("=" * 80)

    # Simulate what orchestrator returns after parsing
    health_analysis_dict = {
        "health_metrics": {
            "cholesterol_total": 220,
            "cholesterol_ldl": 140,
            "cholesterol_hdl": 45,
            "bmi": 27.8
        },
        "risk_tags": ["high_cholesterol", "high_ldl", "overweight"]
    }

    validation_result_dict = {
        "decision": "APPROVE",
        "feedback": ["Plan is well-structured and safe"],
        "violations": []
    }

    # Create Pydantic response model
    response = PlanGenerationResponse(
        session_id="test-123",
        status="approved",
        plan="# Sample Health Plan\n\nTest plan content...",
        risk_tags=["high_cholesterol", "high_ldl", "overweight"],
        iterations=1,
        timestamp="2025-11-26T10:00:00",
        health_analysis=health_analysis_dict,  # Should accept dict
        validation_result=validation_result_dict,  # Should accept dict
        message=None
    )

    print("\n✓ Pydantic model created successfully:")
    print(f"  session_id: {response.session_id}")
    print(f"  status: {response.status}")
    print(f"  health_analysis type: {type(response.health_analysis)}")
    print(f"  validation_result type: {type(response.validation_result)}")
    print(f"  risk_tags: {response.risk_tags}")

    # Verify types
    assert isinstance(response.health_analysis, dict)
    assert isinstance(response.validation_result, dict)
    assert response.health_analysis["health_metrics"]["cholesterol_total"] == 220
    assert response.validation_result["decision"] == "APPROVE"

    print("\n" + "=" * 80)
    print("TEST 3 PASSED: Pydantic validation successful with parsed dicts")
    print("=" * 80)


def main():
    """Run all tests."""
    print("\n" + " JSON PARSING FIX VALIDATION ".center(80, "="))
    print("Testing markdown unwrapping and Pydantic compatibility\n")

    try:
        test_markdown_unwrapping()
        test_agent_output_parsing()
        test_pydantic_validation()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)
        print("\nSummary:")
        print("  ✓ Markdown code blocks are correctly unwrapped")
        print("  ✓ Agent outputs (dict/string/markdown) are parsed to dicts")
        print("  ✓ Pydantic models accept parsed dicts without validation errors")
        print("\nThe fix is working correctly!")
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print("TEST FAILED ✗")
        print("=" * 80)
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    exit(main())

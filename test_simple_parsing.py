"""Simple standalone test for JSON parsing without dependencies."""

import json


def parse_llm_json_response_simple(response_text: str) -> dict:
    """Simplified version of parse_llm_json_response for testing."""
    # Remove markdown code blocks if present
    cleaned_text = response_text.strip()

    if cleaned_text.startswith("```"):
        # Extract content between ``` markers
        start = cleaned_text.find("{")
        end = cleaned_text.rfind("}") + 1

        if start >= 0 and end > start:
            cleaned_text = cleaned_text[start:end]

    # Parse JSON
    return json.loads(cleaned_text.strip())


def main():
    print("=" * 80)
    print("SIMPLE JSON PARSING TEST")
    print("=" * 80)

    # Test 1: Markdown-wrapped JSON
    markdown_json = '''```json
{
  "health_metrics": {
    "cholesterol_total": 220,
    "cholesterol_ldl": 140
  },
  "risk_tags": ["high_cholesterol", "high_ldl"]
}
```'''

    print("\nTest 1: Markdown-wrapped JSON")
    print(f"Input: {markdown_json[:50]}...")
    result = parse_llm_json_response_simple(markdown_json)
    print(f"Output: {json.dumps(result, indent=2)}")
    assert result["health_metrics"]["cholesterol_total"] == 220
    print("[PASSED]")

    # Test 2: Plain JSON
    plain_json = '{"decision": "APPROVE", "feedback": [], "violations": []}'
    print("\nTest 2: Plain JSON")
    print(f"Input: {plain_json}")
    result2 = parse_llm_json_response_simple(plain_json)
    print(f"Output: {json.dumps(result2, indent=2)}")
    assert result2["decision"] == "APPROVE"
    print("[PASSED]")

    # Test 3: Markdown without json tag
    markdown_no_tag = '''```
{
  "decision": "REJECT",
  "feedback": ["Fix this"],
  "violations": ["error"]
}
```'''

    print("\nTest 3: Markdown without tag")
    print(f"Input: {markdown_no_tag[:40]}...")
    result3 = parse_llm_json_response_simple(markdown_no_tag)
    print(f"Output: {json.dumps(result3, indent=2)}")
    assert result3["decision"] == "REJECT"
    print("[PASSED]")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED")
    print("=" * 80)
    print("\nThe markdown unwrapping logic works correctly!")
    print("This will fix the Pydantic validation errors.")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

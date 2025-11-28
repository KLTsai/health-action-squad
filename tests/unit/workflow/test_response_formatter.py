"""Comprehensive tests for ResponseFormatter module.

Tests all edge cases for response formatting, including:
- Markdown-wrapped JSON handling
- Missing/malformed data
- Different validation states
- Error scenarios
"""

import pytest
import json
from src.workflow.response_formatter import ResponseFormatter


class TestResponseFormatterInitialization:
    """Test ResponseFormatter initialization"""

    def test_init_with_default_model(self):
        """Test initialization with default model"""
        formatter = ResponseFormatter()
        assert formatter.model_name == "gemini-2.5-flash"
        assert formatter.logger is not None

    def test_init_with_custom_model(self):
        """Test initialization with custom model"""
        formatter = ResponseFormatter(model_name="gemini-1.5-pro")
        assert formatter.model_name == "gemini-1.5-pro"


class TestFormatSuccessResponse:
    """Test format_success_response method"""

    @pytest.fixture
    def formatter(self):
        return ResponseFormatter()

    def test_format_success_with_valid_state(self, formatter):
        """Test formatting with complete valid state"""
        state = {
            "health_analysis": '{"health_metrics": {"cholesterol": 200}, "risk_tags": ["high_cholesterol"]}',
            "current_plan": "# Health Plan\n\nYour personalized plan...",
            "validation_result": '{"decision": "APPROVE", "feedback": [], "violations": []}'
        }
        result = formatter.format_success_response(
            state, "session-123", "2025-01-01T00:00:00", "gemini-2.5-flash"
        )

        assert result["session_id"] == "session-123"
        assert result["timestamp"] == "2025-01-01T00:00:00"
        assert result["status"] == "approved"
        assert result["plan"] == "# Health Plan\n\nYour personalized plan..."
        assert result["risk_tags"] == ["high_cholesterol"]
        assert result["iterations"] == 1
        assert isinstance(result["health_analysis"], dict)
        assert isinstance(result["validation_result"], dict)
        assert result["workflow_type"] == "adk"
        assert result["model"] == "gemini-2.5-flash"

    def test_format_success_with_markdown_wrapped_json(self, formatter):
        """Test handling of markdown-wrapped JSON"""
        state = {
            "health_analysis": '```json\n{"risk_tags": ["high_bp"]}\n```',
            "current_plan": "plan",
            "validation_result": '```json\n{"decision": "APPROVE"}\n```'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        # Should successfully unwrap and parse
        assert isinstance(result["health_analysis"], dict)
        assert isinstance(result["validation_result"], dict)
        assert result["risk_tags"] == ["high_bp"]

    def test_format_success_with_already_parsed_dict(self, formatter):
        """Test handling when values are already dictionaries"""
        state = {
            "health_analysis": {"risk_tags": ["high_glucose"], "health_metrics": {}},
            "current_plan": "plan",
            "validation_result": {"decision": "APPROVE", "feedback": []}
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert isinstance(result["health_analysis"], dict)
        assert isinstance(result["validation_result"], dict)
        assert result["risk_tags"] == ["high_glucose"]

    def test_format_success_with_missing_health_analysis_key(self, formatter):
        """Test error handling for missing health_analysis key"""
        state = {
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        }

        with pytest.raises(ValueError, match="missing required outputs"):
            formatter.format_success_response(state, "s", "t", "m")

    def test_format_success_with_missing_current_plan_key(self, formatter):
        """Test error handling for missing current_plan key"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "validation_result": '{"decision": "APPROVE"}'
        }

        with pytest.raises(ValueError, match="missing required outputs"):
            formatter.format_success_response(state, "s", "t", "m")

    def test_format_success_with_missing_validation_result_key(self, formatter):
        """Test error handling for missing validation_result key"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan"
        }

        with pytest.raises(ValueError, match="missing required outputs"):
            formatter.format_success_response(state, "s", "t", "m")

    def test_format_success_with_all_missing_keys(self, formatter):
        """Test error handling when all required keys are missing"""
        state = {}

        with pytest.raises(ValueError) as exc_info:
            formatter.format_success_response(state, "s", "t", "m")

        error_msg = str(exc_info.value)
        assert "health_analysis" in error_msg
        assert "current_plan" in error_msg
        assert "validation_result" in error_msg

    def test_format_success_with_empty_risk_tags_list(self, formatter):
        """Test handling of empty risk_tags list"""
        state = {
            "health_analysis": '{"risk_tags": [], "health_metrics": {}}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert result["risk_tags"] == []

    def test_format_success_with_multiple_risk_tags(self, formatter):
        """Test handling of multiple risk tags"""
        state = {
            "health_analysis": '{"risk_tags": ["high_cholesterol", "high_bp", "high_glucose", "obesity", "pre_diabetes"]}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert len(result["risk_tags"]) == 5
        assert "high_cholesterol" in result["risk_tags"]
        assert "pre_diabetes" in result["risk_tags"]

    def test_format_success_with_approve_decision(self, formatter):
        """Test status determination for APPROVE decision"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert result["status"] == "approved"

    def test_format_success_with_reject_decision(self, formatter):
        """Test status determination for REJECT decision"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"decision": "REJECT", "violations": ["too_long"]}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert result["status"] == "rejected"

    def test_format_success_with_missing_decision_field(self, formatter):
        """Test status determination when decision field is missing (defaults to APPROVE)"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"feedback": []}'  # No decision field
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        # Should default to "approved" based on orchestrator.py line 305
        assert result["status"] == "approved"

    def test_format_success_with_iterations_1(self, formatter):
        """Test iteration count when set to 1"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}',
            "_loop_iterations": 1
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert result["iterations"] == 1

    def test_format_success_with_iterations_3(self, formatter):
        """Test iteration count when set to 3"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}',
            "_loop_iterations": 3
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert result["iterations"] == 3

    def test_format_success_with_loop_iterations_metadata_present(self, formatter):
        """Test using _loop_iterations metadata when present"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}',
            "_loop_iterations": 2
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert result["iterations"] == 2

    def test_format_success_with_loop_iterations_metadata_missing(self, formatter):
        """Test fallback when _loop_iterations metadata is missing"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        # Should default to 1 based on orchestrator.py line 311
        assert result["iterations"] == 1

    def test_format_success_with_iterations_fallback_key(self, formatter):
        """Test using 'iterations' fallback key when _loop_iterations is 1"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}',
            "_loop_iterations": 1,
            "iterations": 2
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        # Based on orchestrator.py lines 312-314, should use iterations fallback
        assert result["iterations"] == 2

    def test_format_success_with_malformed_health_analysis_json(self, formatter):
        """Test handling of malformed health_analysis JSON (uses fallback)"""
        state = {
            "health_analysis": '{"risk_tags": [malformed}',  # Invalid JSON
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        # Should use fallback value {}
        assert result["health_analysis"] == {}
        assert result["risk_tags"] == []

    def test_format_success_with_malformed_validation_result_json(self, formatter):
        """Test handling of malformed validation_result JSON (uses fallback)"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{invalid json}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        # Should use fallback value {}
        assert result["validation_result"] == {}
        assert result["status"] == "approved"  # Uses default decision

    def test_format_success_uses_instance_model_name(self, formatter):
        """Test that instance model_name is used when not provided"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t")  # No model_name arg

        assert result["model"] == "gemini-2.5-flash"  # Uses instance default

    def test_format_success_with_custom_model_override(self, formatter):
        """Test that model_name parameter overrides instance model"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t", "custom-model")

        assert result["model"] == "custom-model"

    def test_format_success_with_none_values_in_state(self, formatter):
        """Test handling when state values are None"""
        state = {
            "health_analysis": None,
            "current_plan": None,
            "validation_result": None
        }

        # Should not raise ValueError (keys exist), but parsing will use fallbacks
        result = formatter.format_success_response(state, "s", "t", "m")

        assert result["health_analysis"] == {}
        assert result["validation_result"] == {}
        assert result["plan"] is None  # workflow_state.get("current_plan", "") returns None when value is None
        assert result["risk_tags"] == []

    def test_format_success_with_empty_current_plan(self, formatter):
        """Test handling of empty current_plan"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert result["plan"] == ""


class TestFormatErrorResponse:
    """Test format_error_response method"""

    @pytest.fixture
    def formatter(self):
        return ResponseFormatter()

    def test_format_error_with_value_error(self, formatter):
        """Test error response formatting with ValueError"""
        error = ValueError("Test validation error")
        result = formatter.format_error_response(error, "session-123", "2025-01-01T00:00:00", "m")

        assert result["session_id"] == "session-123"
        assert result["timestamp"] == "2025-01-01T00:00:00"
        assert result["status"] == "fallback"
        assert result["error"] == "Test validation error"
        assert "General Health Recommendations" in result["plan"]
        assert result["iterations"] == 1
        assert result["risk_tags"] == []
        assert result["health_analysis"] == {}
        assert result["validation_result"] == {}
        assert result["message"] == "Unable to generate personalized plan. Providing safe general recommendations."
        assert result["workflow_type"] == "adk"
        assert result["model"] == "m"

    def test_format_error_with_key_error(self, formatter):
        """Test error response formatting with KeyError"""
        error = KeyError("missing_key")
        result = formatter.format_error_response(error, "s", "t", "m")

        assert result["status"] == "fallback"
        assert "missing_key" in result["error"]

    def test_format_error_with_generic_exception(self, formatter):
        """Test error response formatting with generic Exception"""
        error = Exception("Something went wrong")
        result = formatter.format_error_response(error, "s", "t", "m")

        assert result["status"] == "fallback"
        assert result["error"] == "Something went wrong"

    def test_format_error_with_none_message(self, formatter):
        """Test error response when exception has None message"""
        error = Exception()  # No message
        result = formatter.format_error_response(error, "s", "t", "m")

        assert result["status"] == "fallback"
        assert result["error"] == ""  # str(Exception()) returns empty string

    def test_format_error_with_empty_string_message(self, formatter):
        """Test error response when exception has empty string message"""
        error = ValueError("")
        result = formatter.format_error_response(error, "s", "t", "m")

        assert result["error"] == ""

    def test_format_error_uses_instance_model_name(self, formatter):
        """Test that instance model_name is used when not provided"""
        error = ValueError("test")
        result = formatter.format_error_response(error, "s", "t")  # No model_name arg

        assert result["model"] == "gemini-2.5-flash"

    def test_format_error_with_custom_model_override(self, formatter):
        """Test that model_name parameter overrides instance model"""
        error = ValueError("test")
        result = formatter.format_error_response(error, "s", "t", "custom-model")

        assert result["model"] == "custom-model"

    def test_format_error_iterations_always_one(self, formatter):
        """Test that error responses always set iterations to 1"""
        error = Exception("test")
        result = formatter.format_error_response(error, "s", "t", "m")

        # Based on orchestrator.py line 350 comment
        assert result["iterations"] == 1

    def test_format_error_with_none_error(self, formatter):
        """Test error response when error is None"""
        result = formatter.format_error_response(None, "s", "t", "m")

        # str(None) returns "None" but when passed to format_error_response
        # it becomes "" because the error handling expects Exception objects
        # and None.str() doesn't exist - it's handled by the str() function differently
        assert result["error"] == ""  # str(None) in error handling context

    def test_format_error_contains_all_required_fields(self, formatter):
        """Test that error response contains all required fields"""
        error = ValueError("test")
        result = formatter.format_error_response(error, "s", "t", "m")

        required_fields = [
            "session_id", "timestamp", "status", "plan", "risk_tags",
            "iterations", "health_analysis", "validation_result",
            "message", "error", "workflow_type", "model"
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"


class TestCreateSafeFallbackPlan:
    """Test create_safe_fallback_plan method"""

    @pytest.fixture
    def formatter(self):
        return ResponseFormatter()

    def test_create_fallback_plan_with_empty_risk_tags(self, formatter):
        """Test fallback plan generation with empty risk tags"""
        plan = formatter.create_safe_fallback_plan([])

        assert "General Health Recommendations" in plan
        assert "Physical Activity" in plan
        assert "Nutrition" in plan
        assert "Sleep" in plan
        assert "Stress Management" in plan
        assert "Medical Care" in plan
        assert "⚠️" in plan

    def test_create_fallback_plan_with_one_risk_tag(self, formatter):
        """Test fallback plan with single risk tag (currently unused)"""
        plan = formatter.create_safe_fallback_plan(["high_cholesterol"])

        # risk_tags parameter is currently unused, so output should be identical
        assert "General Health Recommendations" in plan

    def test_create_fallback_plan_with_multiple_risk_tags(self, formatter):
        """Test fallback plan with multiple risk tags (currently unused)"""
        plan = formatter.create_safe_fallback_plan([
            "high_cholesterol", "high_bp", "high_glucose", "obesity", "pre_diabetes"
        ])

        # risk_tags parameter is currently unused
        assert "General Health Recommendations" in plan

    def test_create_fallback_plan_with_none_risk_tags(self, formatter):
        """Test fallback plan when risk_tags is None"""
        plan = formatter.create_safe_fallback_plan(None)

        # Should not crash, but type hint expects List[str]
        assert "General Health Recommendations" in plan

    def test_create_fallback_plan_contains_warnings(self, formatter):
        """Test that fallback plan contains appropriate warnings"""
        plan = formatter.create_safe_fallback_plan([])

        assert "⚠️" in plan
        assert "general recommendation" in plan.lower()
        assert "consult" in plan.lower()
        assert "healthcare provider" in plan.lower()

    def test_create_fallback_plan_markdown_format(self, formatter):
        """Test that fallback plan is valid markdown"""
        plan = formatter.create_safe_fallback_plan([])

        # Check for markdown headers
        assert plan.startswith("# General Health Recommendations")
        assert "## General Guidelines" in plan

        # Check for markdown lists
        assert "1. **Physical Activity**" in plan
        assert "2. **Nutrition**" in plan

        # Check for markdown bold
        assert "**⚠️ Important**" in plan

    def test_create_fallback_plan_content_sections(self, formatter):
        """Test that fallback plan contains all expected content sections"""
        plan = formatter.create_safe_fallback_plan([])

        # Based on orchestrator.py lines 368-400
        expected_sections = [
            "150 minutes of moderate aerobic activity",
            "strength training",
            "balanced diet",
            "7-9 hours of quality sleep",
            "relaxation techniques",
            "regular check-ups"
        ]

        for section in expected_sections:
            assert section in plan, f"Missing expected section: {section}"

    def test_create_fallback_plan_is_string(self, formatter):
        """Test that fallback plan returns a string"""
        plan = formatter.create_safe_fallback_plan([])

        assert isinstance(plan, str)
        assert len(plan) > 0

    def test_create_fallback_plan_identical_outputs(self, formatter):
        """Test that multiple calls with same input produce identical output"""
        plan1 = formatter.create_safe_fallback_plan([])
        plan2 = formatter.create_safe_fallback_plan([])

        assert plan1 == plan2


class TestIntegration:
    """Integration tests for complete workflows"""

    @pytest.fixture
    def formatter(self):
        return ResponseFormatter(model_name="gemini-2.5-flash")

    def test_full_workflow_success_to_api_response(self, formatter):
        """Test complete workflow state → API response transformation"""
        # Simulate realistic workflow state
        state = {
            "user_profile": {"age": 30, "gender": "male"},
            "health_report": {"cholesterol": 240},
            "health_analysis": json.dumps({
                "health_metrics": {
                    "total_cholesterol": 240,
                    "hdl": 35,
                    "ldl": 160,
                    "triglycerides": 200
                },
                "risk_tags": ["high_cholesterol", "low_hdl", "high_triglycerides"]
            }),
            "current_plan": "# Personalized Health Plan\n\n## Cardiovascular Health\n\n...",
            "validation_result": json.dumps({
                "decision": "APPROVE",
                "feedback": [],
                "violations": []
            }),
            "_loop_iterations": 2
        }

        result = formatter.format_success_response(state, "s123", "2025-01-01T12:00:00", "gemini-2.5-flash")

        # Verify all expected fields present
        assert result["session_id"] == "s123"
        assert result["timestamp"] == "2025-01-01T12:00:00"
        assert result["status"] == "approved"
        assert result["plan"] == "# Personalized Health Plan\n\n## Cardiovascular Health\n\n..."
        assert result["risk_tags"] == ["high_cholesterol", "low_hdl", "high_triglycerides"]
        assert result["iterations"] == 2
        assert isinstance(result["health_analysis"], dict)
        assert result["health_analysis"]["health_metrics"]["total_cholesterol"] == 240
        assert isinstance(result["validation_result"], dict)
        assert result["validation_result"]["decision"] == "APPROVE"
        assert result["workflow_type"] == "adk"
        assert result["model"] == "gemini-2.5-flash"

    def test_error_to_fallback_response_flow(self, formatter):
        """Test error → fallback response generation flow"""
        error = ValueError("LLM timeout error")

        result = formatter.format_error_response(error, "err-session", "2025-01-01T00:00:00", "gemini-2.5-flash")

        assert result["status"] == "fallback"
        assert result["error"] == "LLM timeout error"
        assert "General Health Recommendations" in result["plan"]
        assert result["risk_tags"] == []
        assert result["iterations"] == 1

    def test_rejected_plan_workflow(self, formatter):
        """Test workflow where plan is rejected"""
        state = {
            "health_analysis": json.dumps({
                "risk_tags": ["high_bp"],
                "health_metrics": {"systolic_bp": 160}
            }),
            "current_plan": "# Plan that was too long and violated word count",
            "validation_result": json.dumps({
                "decision": "REJECT",
                "violations": ["word_count_exceeded"],
                "feedback": ["Plan exceeds 500 word limit"]
            }),
            "_loop_iterations": 3
        }

        result = formatter.format_success_response(state, "s", "t", "m")

        assert result["status"] == "rejected"
        assert result["iterations"] == 3
        assert result["validation_result"]["decision"] == "REJECT"

    def test_markdown_wrapped_complete_workflow(self, formatter):
        """Test complete workflow with markdown-wrapped agent outputs"""
        state = {
            "health_analysis": "```json\n" + json.dumps({
                "risk_tags": ["obesity"],
                "health_metrics": {"bmi": 32}
            }) + "\n```",
            "current_plan": "# Weight Management Plan",
            "validation_result": "```json\n" + json.dumps({
                "decision": "APPROVE",
                "feedback": []
            }) + "\n```"
        }

        result = formatter.format_success_response(state, "s", "t", "m")

        # Should successfully unwrap all markdown
        assert result["status"] == "approved"
        assert isinstance(result["health_analysis"], dict)
        assert result["health_analysis"]["health_metrics"]["bmi"] == 32
        assert isinstance(result["validation_result"], dict)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def formatter(self):
        return ResponseFormatter()

    def test_unicode_characters_in_plan(self, formatter):
        """Test handling of unicode characters in plan"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "# Plan with unicode: ❤️ 健康 🏃‍♂️",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert "❤️" in result["plan"]
        assert "健康" in result["plan"]

    def test_very_long_plan_text(self, formatter):
        """Test handling of very long plan text"""
        long_plan = "# Plan\n\n" + ("Lorem ipsum " * 1000)
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": long_plan,
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        assert len(result["plan"]) > 5000

    def test_special_characters_in_session_id(self, formatter):
        """Test handling of special characters in session_id"""
        state = {
            "health_analysis": '{"risk_tags": []}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(
            state, "session-123-abc_def.xyz", "t", "m"
        )

        assert result["session_id"] == "session-123-abc_def.xyz"

    def test_non_string_risk_tags(self, formatter):
        """Test handling when risk_tags contains non-string values"""
        state = {
            "health_analysis": '{"risk_tags": ["valid", 123, null]}',
            "current_plan": "plan",
            "validation_result": '{"decision": "APPROVE"}'
        }
        result = formatter.format_success_response(state, "s", "t", "m")

        # JSON parser will preserve the list as-is
        assert "valid" in result["risk_tags"]

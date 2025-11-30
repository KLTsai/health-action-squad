"""Pydantic models for FastAPI request and response validation.

This module defines all request and response models for the Health Action Squad API.
All models use Pydantic v2 for validation and serialization.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class HealthReportRequest(BaseModel):
    """Request model for health report submission.

    Attributes:
        health_report: Raw health report data (lab results, vitals, etc.)
        user_profile: Optional user profile data (age, gender, preferences, etc.)
        health_analysis: Optional pre-computed health analysis (optimization for regenerate)
    """

    health_report: Dict = Field(
        ...,
        description="Raw health report data containing lab results, vitals, and other health metrics",
        example={
            "cholesterol_total": 220,
            "cholesterol_ldl": 150,
            "cholesterol_hdl": 40,
            "blood_pressure": "140/90",
            "glucose_fasting": 110,
            "bmi": 28.5,
        },
    )

    user_profile: Optional[Dict] = Field(
        default=None,
        description="Optional user profile data",
        example={
            "age": 45,
            "gender": "male",
            "height_cm": 175,
            "weight_kg": 85,
            "activity_level": "sedentary",
            "dietary_preferences": ["no_red_meat"],
        },
    )

    health_analysis: Optional[Dict] = Field(
        default=None,
        description="Optional pre-computed health analysis from previous request (skips Analyst Agent for faster regeneration)",
        example={
            "summary": "Multiple cardiovascular risk factors identified",
            "risk_tags": ["high_cholesterol", "elevated_blood_pressure"],
        },
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "health_report": {
                    "cholesterol_total": 220,
                    "cholesterol_ldl": 150,
                    "cholesterol_hdl": 40,
                    "blood_pressure": "140/90",
                    "glucose_fasting": 110,
                    "bmi": 28.5,
                },
                "user_profile": {
                    "age": 45,
                    "gender": "male",
                    "height_cm": 175,
                    "weight_kg": 85,
                    "activity_level": "sedentary",
                    "dietary_preferences": ["no_red_meat"],
                },
            }
        }
    )


class PlanGenerationResponse(BaseModel):
    """Response model for successful plan generation.

    Attributes:
        session_id: Unique session identifier
        status: Workflow status (approved, fallback, etc.)
        plan: Generated lifestyle plan in Markdown format
        risk_tags: List of identified risk tags
        iterations: Number of planner-guard iterations performed
        timestamp: ISO timestamp of plan generation
        health_analysis: Optional health analysis from analyst agent
        validation_result: Optional validation result from guard agent
        message: Optional informational message
    """

    session_id: str = Field(
        ..., description="Unique session identifier for tracking"
    )

    status: str = Field(
        ...,
        description="Workflow status (approved, fallback, etc.)",
        example="approved",
    )

    plan: str = Field(
        ..., description="Generated lifestyle plan in Markdown format"
    )

    risk_tags: List[str] = Field(
        default_factory=list,
        description="List of identified risk tags",
        example=["high_cholesterol", "elevated_blood_pressure", "overweight"],
    )

    iterations: int = Field(
        default=1,
        description="Number of planner-guard iterations performed",
        ge=1,
        le=3,
    )

    timestamp: str = Field(
        ..., description="ISO timestamp of plan generation"
    )

    health_analysis: Optional[Dict] = Field(
        default=None,
        description="Health analysis from analyst agent",
    )

    validation_result: Optional[Dict] = Field(
        default=None,
        description="Validation result from guard agent",
    )

    message: Optional[str] = Field(
        default=None,
        description="Optional informational message",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "approved",
                "plan": "# Personalized Health Plan\n\n## Overview\n...",
                "risk_tags": ["high_cholesterol", "elevated_blood_pressure"],
                "iterations": 1,
                "timestamp": "2025-11-21T10:30:00.000000",
                "health_analysis": {
                    "summary": "Analysis complete",
                    "key_findings": ["Elevated LDL cholesterol"],
                },
                "validation_result": {
                    "decision": "APPROVE",
                    "feedback": "Plan meets all safety criteria",
                },
            }
        }
    )


class ErrorResponse(BaseModel):
    """Response model for error cases.

    Attributes:
        error: Error type or brief message
        detail: Optional detailed error description
        timestamp: ISO timestamp when error occurred
        session_id: Optional session identifier if available
    """

    error: str = Field(..., description="Error type or brief message")

    detail: Optional[str] = Field(
        default=None, description="Detailed error description"
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp when error occurred",
    )

    session_id: Optional[str] = Field(
        default=None, description="Session identifier if available"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "detail": "health_report field is required",
                "timestamp": "2025-11-21T10:30:00.000000",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint.

    Attributes:
        status: Service status (healthy, degraded, unhealthy)
        version: API version
        timestamp: ISO timestamp of health check
        model: Model name being used
        uptime_seconds: Optional uptime in seconds
    """

    status: str = Field(
        ...,
        description="Service status",
        example="healthy",
        pattern="^(healthy|degraded|unhealthy)$",
    )

    version: str = Field(..., description="API version", example="1.0.0")

    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of health check",
    )

    model: str = Field(
        default="gemini-2.5-flash", description="Model name being used"
    )

    uptime_seconds: Optional[float] = Field(
        default=None, description="Service uptime in seconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-11-21T10:30:00.000000",
                "model": "gemini-2.5-flash",
                "uptime_seconds": 3600.5,
            }
        }
    )


class UploadReportRequest(BaseModel):
    """Request model for file upload with optional user profile data.

    Attributes:
        age: Optional user age in years
        gender: Optional user gender
        dietary_restrictions: Optional dietary restrictions (JSON string or list)
        health_goal: Optional primary health goal
        exercise_barriers: Optional exercise barriers (JSON string or list)
    """

    age: Optional[int] = Field(
        default=None,
        description="User age in years",
        ge=0,
        le=150,
        example=45,
    )

    gender: Optional[str] = Field(
        default=None,
        description="User gender (male/female/other)",
        example="male",
        pattern="^(male|female|other)$",
    )

    dietary_restrictions: Optional[str] = Field(
        default=None,
        description="Dietary restrictions as JSON string or comma-separated list",
        example='["no_red_meat", "gluten_free"]',
    )

    health_goal: Optional[str] = Field(
        default=None,
        description="Primary health goal",
        example="Lower cholesterol and lose weight",
    )

    exercise_barriers: Optional[str] = Field(
        default=None,
        description="Exercise barriers as JSON string or comma-separated list",
        example='["limited_time", "joint_pain"]',
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "age": 45,
                "gender": "male",
                "dietary_restrictions": '["no_red_meat", "gluten_free"]',
                "health_goal": "Lower cholesterol and lose weight",
                "exercise_barriers": '["limited_time"]',
            }
        }
    )


class MultiFileUploadStats(BaseModel):
    """Statistics for multi-file upload processing.

    Attributes:
        total_files: Total number of files uploaded
        successfully_parsed: Number of files parsed successfully
        failed_files: List of filenames that failed to parse
        total_size_bytes: Total size of all uploaded files
        parsing_time_seconds: Total time spent parsing all files
    """

    total_files: int = Field(
        ..., description="Total number of files uploaded", ge=1
    )

    successfully_parsed: int = Field(
        ..., description="Number of files parsed successfully", ge=0
    )

    failed_files: List[str] = Field(
        default_factory=list,
        description="List of filenames that failed validation or parsing",
    )

    total_size_bytes: int = Field(
        ..., description="Total size of all uploaded files in bytes", ge=0
    )

    parsing_time_seconds: Optional[float] = Field(
        default=None, description="Total time spent parsing in seconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_files": 3,
                "successfully_parsed": 3,
                "failed_files": [],
                "total_size_bytes": 1024000,
                "parsing_time_seconds": 2.5,
            }
        }
    )


class ParsedReportResponse(BaseModel):
    """Response model for parsed health report with generated plan.

    Attributes:
        session_id: Unique session identifier
        status: Workflow status (approved, fallback, etc.)
        plan: Generated lifestyle plan in Markdown format
        parsed_data: Preview of parsed health data from uploaded file
        risk_tags: List of identified risk tags
        iterations: Number of planner-guard iterations performed
        timestamp: ISO timestamp of processing
        health_analysis: Optional health analysis from analyst agent
        validation_result: Optional validation result from guard agent
        message: Optional informational message
    """

    session_id: str = Field(
        ..., description="Unique session identifier for tracking"
    )

    status: str = Field(
        ...,
        description="Workflow status (approved, fallback, etc.)",
        example="approved",
    )

    plan: str = Field(
        ..., description="Generated lifestyle plan in Markdown format"
    )

    parsed_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Preview of parsed data from uploaded health report",
        example={
            "total_cholesterol": 220,
            "ldl_cholesterol": 150,
            "hdl_cholesterol": 40,
            "blood_pressure": "140/90",
            "fasting_glucose": 110,
            "bmi": 28.5,
        },
    )

    risk_tags: List[str] = Field(
        default_factory=list,
        description="List of identified risk tags",
        example=["high_cholesterol", "elevated_blood_pressure", "overweight"],
    )

    iterations: int = Field(
        default=1,
        description="Number of planner-guard iterations performed",
        ge=1,
        le=3,
    )

    timestamp: str = Field(
        ..., description="ISO timestamp of plan generation"
    )

    health_analysis: Optional[Dict] = Field(
        default=None,
        description="Health analysis from analyst agent",
    )

    validation_result: Optional[Dict] = Field(
        default=None,
        description="Validation result from guard agent",
    )

    message: Optional[str] = Field(
        default=None,
        description="Optional informational message",
    )

    upload_stats: Optional[MultiFileUploadStats] = Field(
        default=None,
        description="Statistics for multi-file uploads (only present when files uploaded)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "approved",
                "plan": "# Personalized Health Plan\n\n## Overview\n...",
                "parsed_data": {
                    "total_cholesterol": 220,
                    "ldl_cholesterol": 150,
                    "hdl_cholesterol": 40,
                    "blood_pressure": "140/90",
                    "fasting_glucose": 110,
                    "bmi": 28.5,
                },
                "risk_tags": ["high_cholesterol", "elevated_blood_pressure"],
                "iterations": 1,
                "timestamp": "2025-11-21T10:30:00.000000",
                "health_analysis": {
                    "summary": "Analysis complete",
                    "key_findings": ["Elevated LDL cholesterol"],
                },
                "validation_result": {
                    "decision": "APPROVE",
                    "feedback": "Plan meets all safety criteria",
                },
                "upload_stats": {
                    "total_files": 3,
                    "successfully_parsed": 3,
                    "failed_files": [],
                    "total_size_bytes": 1024000,
                    "parsing_time_seconds": 2.5,
                },
            }
        }
    )

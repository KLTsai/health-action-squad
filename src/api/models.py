"""Pydantic models for FastAPI request and response validation.

This module defines all request and response models for the Health Action Squad API.
All models use Pydantic v2 for validation and serialization.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class HealthReportRequest(BaseModel):
    """Request model for health report submission.

    Attributes:
        health_report: Raw health report data (lab results, vitals, etc.)
        user_profile: Optional user profile data (age, gender, preferences, etc.)
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

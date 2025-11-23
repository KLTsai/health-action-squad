"""FastAPI server for Health Action Squad.

This module implements the REST API for the Health Action Squad health concierge service.
It exposes endpoints for health report analysis and lifestyle plan generation.
"""

import json
import time
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request, status, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.workflow.orchestrator import Orchestrator
from src.common.config import Config
from src.utils.logger import get_logger
from src.ai.parser import HealthReportParser
from .models import (
    HealthReportRequest,
    PlanGenerationResponse,
    ErrorResponse,
    HealthCheckResponse,
    UploadReportRequest,
    ParsedReportResponse,
)
from .middleware import setup_middleware

# Initialize logger
logger = get_logger(__name__)

# Track server start time for uptime calculation
SERVER_START_TIME = time.time()

# Create FastAPI application
app = FastAPI(
    title="Health Action Squad API",
    description="AI-powered health concierge service for personalized lifestyle planning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on deployment needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup rate limiting middleware
setup_middleware(app)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all uncaught exceptions.

    Args:
        request: FastAPI request object
        exc: Exception that was raised

    Returns:
        JSONResponse with error details
    """
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat(),
        ).model_dump(),
    )


# Health check endpoints
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="Health check endpoint",
    description="Returns the health status of the API service",
)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint.

    Returns:
        HealthCheckResponse with service status and metadata
    """
    uptime = time.time() - SERVER_START_TIME

    logger.info("Health check requested", uptime_seconds=uptime)

    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        model=Config.MODEL_NAME,
        uptime_seconds=uptime,
    )


@app.get(
    "/api/v1/health",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="API v1 health check",
    description="Returns the health status of the API service (v1 endpoint)",
)
async def api_health_check() -> HealthCheckResponse:
    """API v1 health check endpoint (alias).

    Returns:
        HealthCheckResponse with service status and metadata
    """
    return await health_check()


# Main plan generation endpoint
@app.post(
    "/api/v1/generate_plan",
    response_model=PlanGenerationResponse,
    tags=["Plan Generation"],
    summary="Generate personalized health plan",
    description="Analyzes health report and generates personalized lifestyle plan with safety validation",
    responses={
        200: {
            "description": "Plan generated successfully",
            "model": PlanGenerationResponse,
        },
        400: {
            "description": "Invalid request data",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def generate_plan(request: HealthReportRequest) -> PlanGenerationResponse:
    """Generate personalized lifestyle plan from health report.

    This endpoint:
    1. Receives health report and optional user profile
    2. Validates input data
    3. Executes ADK workflow (Analyst → Planner → Guard loop)
    4. Returns generated plan with validation results

    Args:
        request: HealthReportRequest containing health report and optional user profile

    Returns:
        PlanGenerationResponse with generated plan and metadata

    Raises:
        HTTPException: If workflow execution fails
    """
    logger.info(
        "Plan generation requested",
        has_user_profile=request.user_profile is not None,
        health_report_keys=list(request.health_report.keys()),
    )

    try:
        # Initialize orchestrator
        orchestrator = Orchestrator(model_name=Config.MODEL_NAME)

        # Execute ADK workflow (async)
        result = await orchestrator.execute(
            health_report=request.health_report,
            user_profile=request.user_profile,
        )

        # Log successful completion
        logger.info(
            "Plan generation completed",
            session_id=result.get("session_id"),
            status=result.get("status"),
            iterations=result.get("iterations", 1),
        )

        # Convert orchestrator result to response model
        response = PlanGenerationResponse(
            session_id=result["session_id"],
            status=result["status"],
            plan=result.get("plan", ""),
            risk_tags=result.get("risk_tags", []),
            iterations=result.get("iterations", 1),
            timestamp=result.get("timestamp", datetime.utcnow().isoformat()),
            health_analysis=result.get("health_analysis"),
            validation_result=result.get("validation_result"),
            message=result.get("message"),
        )

        return response

    except ValueError as e:
        # Validation errors
        logger.warning(
            "Validation error during plan generation",
            error=str(e),
            exc_info=False,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="ValidationError",
                detail=str(e),
                timestamp=datetime.utcnow().isoformat(),
            ).model_dump(),
        )

    except Exception as e:
        # Unexpected errors
        logger.error(
            "Unexpected error during plan generation",
            error=str(e),
            exc_info=True,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="InternalServerError",
                detail="An unexpected error occurred during plan generation",
                timestamp=datetime.utcnow().isoformat(),
            ).model_dump(),
        )


# File upload endpoint
@app.post(
    "/api/v1/upload_report",
    response_model=ParsedReportResponse,
    tags=["Report Upload"],
    summary="Upload health report and generate plan",
    description="Accepts PDF or image file uploads of health reports, parses them, merges with optional user data, and generates personalized health plan",
    responses={
        200: {
            "description": "Report processed successfully",
            "model": ParsedReportResponse,
        },
        400: {
            "description": "Invalid file or request data",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def upload_report(
    file: UploadFile = File(..., description="Health report file (PDF, JPG, or PNG)"),
    age: Optional[int] = Form(None, description="User age in years", ge=0, le=150),
    gender: Optional[str] = Form(
        None,
        description="User gender (male/female/other)",
        regex="^(male|female|other)$",
    ),
    dietary_restrictions: Optional[str] = Form(
        None, description="Dietary restrictions as JSON string or comma-separated list"
    ),
    health_goal: Optional[str] = Form(
        None, description="Primary health goal"
    ),
    exercise_barriers: Optional[str] = Form(
        None, description="Exercise barriers as JSON string or comma-separated list"
    ),
) -> ParsedReportResponse:
    """Upload health report file and generate personalized plan.

    This endpoint:
    1. Validates uploaded file (size, format)
    2. Parses health data from file (PDF/image)
    3. Merges parsed data with optional user input
    4. Executes ADK workflow (Analyst → Planner → Guard loop)
    5. Returns generated plan with parsed data preview

    Args:
        file: Uploaded health report file (PDF, JPG, PNG)
        age: Optional user age
        gender: Optional user gender
        dietary_restrictions: Optional dietary restrictions
        health_goal: Optional primary health goal
        exercise_barriers: Optional exercise barriers

    Returns:
        ParsedReportResponse with generated plan and parsed data preview

    Raises:
        HTTPException: If file validation or processing fails
    """
    logger.info(
        "File upload started",
        filename=file.filename,
        content_type=file.content_type,
        has_user_age=age is not None,
        has_user_gender=gender is not None,
    )

    try:
        # Step 1: Save uploaded file to temporary location
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / (file.filename or "report")
            file_content = await file.read()

            # Write file to temp location
            with temp_path.open("wb") as f:
                f.write(file_content)

            logger.info(
                "File saved to temporary location",
                temp_path=str(temp_path),
                file_size=len(file_content),
            )

            # Step 2: Validate file
            validation_result = HealthReportParser.validate_file(temp_path)
            if not validation_result["valid"]:
                logger.warning(
                    "File validation failed",
                    error=validation_result["error"],
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="FileValidationError",
                        detail=validation_result["error"],
                        timestamp=datetime.utcnow().isoformat(),
                    ).model_dump(),
                )

            # Step 3: Parse health report from file
            parsed_result = await HealthReportParser.parse_report(temp_path)
            if not parsed_result["parsed_successfully"]:
                logger.warning(
                    "File parsing failed",
                    error=parsed_result["error"],
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="FileParsingError",
                        detail=parsed_result["error"],
                        timestamp=datetime.utcnow().isoformat(),
                    ).model_dump(),
                )

            # Step 4: Prepare user profile from form fields
            user_profile = {}
            if age is not None:
                user_profile["age"] = age
            if gender is not None:
                user_profile["gender"] = gender
            if health_goal is not None:
                user_profile["health_goal"] = health_goal

            # Parse dietary_restrictions (handle both JSON and comma-separated)
            if dietary_restrictions is not None:
                try:
                    # Try parsing as JSON first
                    user_profile["dietary_restrictions"] = json.loads(
                        dietary_restrictions
                    )
                except json.JSONDecodeError:
                    # Fall back to comma-separated list
                    user_profile["dietary_restrictions"] = [
                        s.strip() for s in dietary_restrictions.split(",")
                    ]

            # Parse exercise_barriers (handle both JSON and comma-separated)
            if exercise_barriers is not None:
                try:
                    # Try parsing as JSON first
                    user_profile["exercise_barriers"] = json.loads(
                        exercise_barriers
                    )
                except json.JSONDecodeError:
                    # Fall back to comma-separated list
                    user_profile["exercise_barriers"] = [
                        s.strip() for s in exercise_barriers.split(",")
                    ]

            # Step 5: Merge parsed data with user input
            extracted_metrics = parsed_result.get("extracted_metrics", {})
            merged_health_report = HealthReportParser.merge_parsed_with_user_input(
                extracted_metrics, user_profile if user_profile else None
            )

            logger.info(
                "Health report prepared",
                parsed_keys=list(extracted_metrics.keys()),
                user_profile_keys=list(user_profile.keys()),
            )

            # Step 6: Execute ADK workflow
            orchestrator = Orchestrator(model_name=Config.MODEL_NAME)

            result = await orchestrator.execute(
                health_report=merged_health_report,
                user_profile=user_profile if user_profile else None,
            )

            logger.info(
                "Plan generation completed",
                session_id=result.get("session_id"),
                status=result.get("status"),
                iterations=result.get("iterations", 1),
            )

            # Step 7: Format response with parsed data preview
            response = ParsedReportResponse(
                session_id=result["session_id"],
                status=result["status"],
                plan=result.get("plan", ""),
                parsed_data=extracted_metrics,  # Include preview of parsed data
                risk_tags=result.get("risk_tags", []),
                iterations=result.get("iterations", 1),
                timestamp=result.get("timestamp", datetime.utcnow().isoformat()),
                health_analysis=result.get("health_analysis"),
                validation_result=result.get("validation_result"),
                message=result.get("message"),
            )

            logger.info(
                "File upload completed successfully",
                session_id=response.session_id,
                status=response.status,
            )

            return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ValueError as e:
        # Validation errors
        logger.warning(
            "Validation error during file upload",
            error=str(e),
            exc_info=False,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="ValidationError",
                detail=str(e),
                timestamp=datetime.utcnow().isoformat(),
            ).model_dump(),
        )

    except Exception as e:
        # Unexpected errors
        logger.error(
            "Unexpected error during file upload",
            error=str(e),
            filename=file.filename,
            exc_info=True,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="InternalServerError",
                detail="An unexpected error occurred while processing the uploaded file",
                timestamp=datetime.utcnow().isoformat(),
            ).model_dump(),
        )


# Root endpoint
@app.get(
    "/",
    tags=["Info"],
    summary="API information",
    description="Returns basic information about the Health Action Squad API",
)
async def root() -> Dict[str, str]:
    """Root endpoint with API information.

    Returns:
        Dict with API name, version, and documentation URL
    """
    return {
        "name": "Health Action Squad API",
        "version": "1.0.0",
        "description": "AI-powered health concierge service for personalized lifestyle planning",
        "docs": "/docs",
        "health": "/health",
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Execute on application startup."""
    logger.info(
        "Health Action Squad API starting",
        version="1.0.0",
        model=Config.MODEL_NAME,
        host=Config.API_HOST,
        port=Config.API_PORT,
    )


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Execute on application shutdown."""
    uptime = time.time() - SERVER_START_TIME
    logger.info(
        "Health Action Squad API shutting down",
        uptime_seconds=uptime,
    )

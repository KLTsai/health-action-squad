"""FastAPI server for Health Action Squad.

This module implements the REST API for the Health Action Squad health concierge service.
It exposes endpoints for health report analysis and lifestyle plan generation.
"""

import time
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.workflow.orchestrator import Orchestrator
from src.common.config import Config
from src.utils.logger import get_logger
from .models import (
    HealthReportRequest,
    PlanGenerationResponse,
    ErrorResponse,
    HealthCheckResponse,
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

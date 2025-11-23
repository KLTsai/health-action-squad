"""FastAPI server for Health Action Squad.

This module implements the REST API for the Health Action Squad health concierge service.
It exposes endpoints for health report analysis and lifestyle plan generation.
"""

import json
import time
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

from fastapi import FastAPI, HTTPException, Request, status, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.workflow.orchestrator import Orchestrator
from src.common.config import Config
from src.utils.logger import get_logger
from src.parsers import HealthReportParser as OCRParser
from src.ai.parser import HealthReportParser as LegacyParser
from .models import (
    HealthReportRequest,
    PlanGenerationResponse,
    ErrorResponse,
    HealthCheckResponse,
    UploadReportRequest,
    ParsedReportResponse,
    MultiFileUploadStats,
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


def validate_multi_file_upload(files: List[UploadFile]) -> Dict[str, Any]:
    """Validate multi-file upload constraints.

    Args:
        files: List of uploaded files

    Returns:
        Dict with validation result:
        {
            "valid": bool,
            "error": Optional[str],
            "total_size": int,
            "file_count": int
        }
    """
    # Validation rules from Config
    MAX_FILES = Config.MAX_UPLOAD_FILES
    MAX_TOTAL_SIZE = Config.MAX_TOTAL_UPLOAD_SIZE

    if not files:
        return {
            "valid": False,
            "error": "No files provided",
            "total_size": 0,
            "file_count": 0,
        }

    if len(files) > MAX_FILES:
        return {
            "valid": False,
            "error": f"Too many files. Maximum {MAX_FILES} files allowed, got {len(files)}",
            "total_size": 0,
            "file_count": len(files),
        }

    # Check total size (estimate from file size if available)
    total_size = 0
    for file in files:
        # Note: size may not always be available before reading
        file_size = getattr(file, "size", 0) or 0
        total_size += file_size

    if total_size > 0 and total_size > MAX_TOTAL_SIZE:
        return {
            "valid": False,
            "error": f"Total file size {total_size} bytes exceeds maximum {MAX_TOTAL_SIZE} bytes",
            "total_size": total_size,
            "file_count": len(files),
        }

    return {
        "valid": True,
        "error": None,
        "total_size": total_size,
        "file_count": len(files),
    }


# File upload endpoint
@app.post(
    "/api/v1/upload_report",
    response_model=ParsedReportResponse,
    tags=["Report Upload"],
    summary="Upload health report and generate plan",
    description="Accepts multiple PDF or image file uploads of health reports (multi-page support), parses them, merges with optional user data, and generates personalized health plan",
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
    files: List[UploadFile] = File(
        ...,
        description="Health report files (PDF, JPG, or PNG). Upload multiple pages of same report. Maximum 10 files, 50MB total.",
    ),
    age: Optional[int] = Form(None, description="User age in years", ge=0, le=150),
    gender: Optional[str] = Form(
        None,
        description="User gender (male/female/other)",
        regex="^(male|female|other)$",
    ),
    dietary_restrictions: Optional[str] = Form(
        None, description="Dietary restrictions as JSON string or comma-separated list"
    ),
    health_goal: Optional[str] = Form(None, description="Primary health goal"),
    exercise_barriers: Optional[str] = Form(
        None, description="Exercise barriers as JSON string or comma-separated list"
    ),
) -> ParsedReportResponse:
    """Upload health report files and generate personalized plan.

    This endpoint:
    1. Validates uploaded files (count, size, format)
    2. Parses health data from files (PDF/image) using batch processing
    3. Merges parsed data with optional user input
    4. Executes ADK workflow (Analyst → Planner → Guard loop)
    5. Returns generated plan with parsed data preview and upload statistics

    Args:
        files: Uploaded health report files (PDF, JPG, PNG) - up to 10 files
        age: Optional user age
        gender: Optional user gender
        dietary_restrictions: Optional dietary restrictions
        health_goal: Optional primary health goal
        exercise_barriers: Optional exercise barriers

    Returns:
        ParsedReportResponse with generated plan, parsed data, and upload stats

    Raises:
        HTTPException: If file validation or processing fails
    """
    logger.info(
        "Multi-file upload started",
        file_count=len(files),
        filenames=[f.filename for f in files],
        has_user_age=age is not None,
        has_user_gender=gender is not None,
    )

    try:
        # Step 1: Validate multi-file upload constraints
        validation = validate_multi_file_upload(files)
        if not validation["valid"]:
            logger.warning("Multi-file validation failed", error=validation["error"])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error="MultiFileValidationError",
                    detail=validation["error"],
                    timestamp=datetime.utcnow().isoformat(),
                ).model_dump(),
            )

        # Step 2: Save all uploaded files to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_paths = []
            file_sizes = []

            # Save all files
            for idx, file in enumerate(files):
                temp_path = Path(temp_dir) / f"{idx}_{file.filename or f'report_{idx}'}"
                file_content = await file.read()

                with temp_path.open("wb") as f:
                    f.write(file_content)

                temp_paths.append(str(temp_path))
                file_sizes.append(len(file_content))

                logger.info(
                    "File saved",
                    index=idx,
                    filename=file.filename,
                    size=len(file_content),
                )

            # Step 3: Validate each file individually
            failed_files = []
            for temp_path in temp_paths:
                validation_result = LegacyParser.validate_file(Path(temp_path))
                if not validation_result["valid"]:
                    failed_files.append(Path(temp_path).name)
                    logger.warning(
                        "File validation failed",
                        file=Path(temp_path).name,
                        error=validation_result["error"],
                    )

            # If ALL files failed, return error
            if len(failed_files) == len(files):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error="AllFilesInvalid",
                        detail=f"All uploaded files failed validation: {', '.join(failed_files)}",
                        timestamp=datetime.utcnow().isoformat(),
                    ).model_dump(),
                )

            # Filter out failed files for parsing (partial success allowed)
            valid_paths = [
                p for p in temp_paths if Path(p).name not in failed_files
            ]

            logger.info(
                "File validation completed",
                total_files=len(files),
                valid_files=len(valid_paths),
                failed_files=len(failed_files),
            )

            # Step 4: Parse health reports using batch parser
            start_time = time.time()

            parser = OCRParser(
                min_completeness_threshold=0.7,
                use_llm_fallback=True,
                preprocess_images=True,
                session_id=None,
            )

            batch_result = await parser.parse_batch(
                file_paths=valid_paths, merge_results=True
            )

            parsing_time = time.time() - start_time

            # Extract merged data
            extracted_metrics = batch_result.get("merged_data", {})
            overall_completeness = batch_result.get("overall_completeness", 0.0)
            individual_results = batch_result.get("results", [])

            # Determine parsing source (aggregate across files)
            sources = [r.get("source", "unknown") for r in individual_results]
            parsing_source = "hybrid" if "hybrid" in sources else "ocr"

            logger.info(
                "Batch OCR parsing completed",
                file_count=len(valid_paths),
                completeness=overall_completeness,
                source=parsing_source,
                fields_extracted=len(extracted_metrics),
                parsing_time=parsing_time,
            )

            # Prepare upload stats
            upload_stats = MultiFileUploadStats(
                total_files=len(files),
                successfully_parsed=len(valid_paths),
                failed_files=failed_files,
                total_size_bytes=sum(file_sizes),
                parsing_time_seconds=round(parsing_time, 2),
            )

            # Step 5: Prepare user profile from form fields
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
            merged_health_report = LegacyParser.merge_parsed_with_user_input(
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

            # Step 7: Format response with parsed data preview and upload stats
            response = ParsedReportResponse(
                session_id=result["session_id"],
                status=result["status"],
                plan=result.get("plan", ""),
                parsed_data=extracted_metrics,  # Include preview of merged parsed data
                risk_tags=result.get("risk_tags", []),
                iterations=result.get("iterations", 1),
                timestamp=result.get("timestamp", datetime.utcnow().isoformat()),
                health_analysis=result.get("health_analysis"),
                validation_result=result.get("validation_result"),
                message=result.get("message"),
                upload_stats=upload_stats,  # Include multi-file upload statistics
            )

            logger.info(
                "Multi-file upload completed successfully",
                session_id=response.session_id,
                status=response.status,
                files_processed=upload_stats.successfully_parsed,
                total_files=upload_stats.total_files,
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
            "Unexpected error during multi-file upload",
            error=str(e),
            file_count=len(files),
            filenames=[f.filename for f in files],
            exc_info=True,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="InternalServerError",
                detail="An unexpected error occurred while processing the uploaded files",
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

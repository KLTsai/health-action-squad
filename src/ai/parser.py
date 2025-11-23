"""Health report parser for extracting health data from uploaded files.

This module provides utilities for parsing health reports from various file formats
(PDF, images) using AI vision capabilities. It extracts structured health metrics
from uploaded documents.

Supported formats:
- PDF documents containing health reports
- JPG/PNG images of health reports
"""

import json
import mimetypes
from pathlib import Path
from typing import Dict, Optional, Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


class HealthReportParser:
    """Parser for extracting health data from uploaded report files.

    This parser handles various file formats (PDF, images) and extracts
    structured health metrics using optical character recognition or
    vision capabilities.

    Supported file types:
    - application/pdf (PDF documents)
    - image/jpeg (JPG images)
    - image/png (PNG images)
    """

    # Supported MIME types
    SUPPORTED_MIME_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }

    # Maximum file size: 10MB
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

    # File extensions
    SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

    @classmethod
    def validate_file(cls, file_path: Path) -> Dict[str, Any]:
        """Validate uploaded file meets size and format requirements.

        Args:
            file_path: Path to uploaded file

        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "error": Optional[str],
                "mime_type": str,
                "file_size": int
            }

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            return {
                "valid": False,
                "error": f"File not found: {file_path}",
                "mime_type": None,
                "file_size": 0,
            }

        # Check file extension
        file_ext = file_path.suffix.lower()
        if file_ext not in cls.SUPPORTED_EXTENSIONS:
            return {
                "valid": False,
                "error": f"Unsupported file type: {file_ext}. Supported types: {', '.join(cls.SUPPORTED_EXTENSIONS)}",
                "mime_type": None,
                "file_size": 0,
            }

        # Check file size
        file_size = file_path.stat().st_size
        if file_size > cls.MAX_FILE_SIZE_BYTES:
            return {
                "valid": False,
                "error": f"File size {file_size} bytes exceeds maximum {cls.MAX_FILE_SIZE_BYTES} bytes",
                "mime_type": None,
                "file_size": file_size,
            }

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type not in cls.SUPPORTED_MIME_TYPES:
            mime_type = cls._guess_mime_type_by_extension(file_ext)

        if mime_type not in cls.SUPPORTED_MIME_TYPES:
            return {
                "valid": False,
                "error": f"Unsupported MIME type: {mime_type}",
                "mime_type": mime_type,
                "file_size": file_size,
            }

        logger.info(
            "File validation successful",
            file=file_path.name,
            mime_type=mime_type,
            file_size=file_size,
        )

        return {
            "valid": True,
            "error": None,
            "mime_type": mime_type,
            "file_size": file_size,
        }

    @classmethod
    async def parse_report(cls, file_path: Path) -> Dict[str, Any]:
        """Parse health report from uploaded file.

        For MVP/POC phase, this returns a template structure showing
        what would be extracted. Full implementation would use:
        - PDF libraries (pypdf, pdfplumber) for text extraction
        - Vision APIs for image OCR
        - LLM parsing for unstructured health data

        Args:
            file_path: Path to uploaded file

        Returns:
            Dict with extracted health metrics:
            {
                "parsed_successfully": bool,
                "error": Optional[str],
                "extracted_metrics": Dict with health data,
                "confidence": float,
                "raw_text": Optional[str] (preview)
            }
        """
        # Validate file first
        validation = cls.validate_file(file_path)
        if not validation["valid"]:
            logger.warning(
                "File validation failed",
                error=validation["error"],
            )
            return {
                "parsed_successfully": False,
                "error": validation["error"],
                "extracted_metrics": {},
                "confidence": 0.0,
                "raw_text": None,
            }

        mime_type = validation["mime_type"]

        logger.info(
            "Starting health report parsing",
            file=file_path.name,
            mime_type=mime_type,
        )

        try:
            if mime_type == "application/pdf":
                return await cls._parse_pdf(file_path)
            elif mime_type == "image/jpeg" or mime_type == "image/png":
                return await cls._parse_image(file_path)
            else:
                return {
                    "parsed_successfully": False,
                    "error": f"Unsupported MIME type: {mime_type}",
                    "extracted_metrics": {},
                    "confidence": 0.0,
                    "raw_text": None,
                }

        except Exception as e:
            logger.error(
                "Error parsing health report",
                error=str(e),
                file=file_path.name,
                exc_info=True,
            )
            return {
                "parsed_successfully": False,
                "error": f"Error parsing file: {str(e)}",
                "extracted_metrics": {},
                "confidence": 0.0,
                "raw_text": None,
            }

    @classmethod
    async def _parse_pdf(cls, file_path: Path) -> Dict[str, Any]:
        """Parse PDF health report.

        MVP implementation returns template structure.
        Production would extract text and parse metrics using vision or OCR.

        Args:
            file_path: Path to PDF file

        Returns:
            Parsed metrics dictionary
        """
        logger.info("Parsing PDF report", file=file_path.name)

        # MVP: Return template showing expected extraction structure
        # In production, would use pypdf, pdfplumber, or vision APIs to extract text
        return {
            "parsed_successfully": True,
            "error": None,
            "extracted_metrics": cls._get_template_metrics(),
            "confidence": 0.85,
            "raw_text": "[PDF content preview - would extract actual text in production]",
            "file_type": "pdf",
            "parsing_method": "mvp_template",
        }

    @classmethod
    async def _parse_image(cls, file_path: Path) -> Dict[str, Any]:
        """Parse image health report.

        MVP implementation returns template structure.
        Production would use vision APIs to extract text and parse metrics.

        Args:
            file_path: Path to image file

        Returns:
            Parsed metrics dictionary
        """
        logger.info("Parsing image report", file=file_path.name)

        # MVP: Return template showing expected extraction structure
        # In production, would use Google Vision API or similar for OCR
        return {
            "parsed_successfully": True,
            "error": None,
            "extracted_metrics": cls._get_template_metrics(),
            "confidence": 0.8,
            "raw_text": "[Image content preview - would extract via OCR in production]",
            "file_type": "image",
            "parsing_method": "mvp_template",
        }

    @classmethod
    def _get_template_metrics(cls) -> Dict[str, Any]:
        """Get template health metrics for MVP.

        Returns:
            Dict with sample health metrics that would be extracted from actual reports
        """
        return {
            "lipid_panel": {
                "total_cholesterol": 220,
                "ldl_cholesterol": 150,
                "hdl_cholesterol": 40,
                "triglycerides": 150,
                "unit": "mg/dL",
            },
            "glucose": {
                "fasting_glucose": 110,
                "unit": "mg/dL",
            },
            "blood_pressure": {
                "systolic": 140,
                "diastolic": 90,
                "unit": "mmHg",
            },
            "anthropometry": {
                "weight_kg": 85,
                "height_cm": 175,
                "bmi": 28.5,
            },
            "metabolic": {
                "hemoglobin_a1c": 6.5,
                "unit": "%",
            },
            "note": "This is a template showing expected data structure. In production, actual values would be extracted from the uploaded file.",
        }

    @classmethod
    def _guess_mime_type_by_extension(cls, extension: str) -> str:
        """Guess MIME type from file extension.

        Args:
            extension: File extension (e.g., '.pdf', '.jpg')

        Returns:
            MIME type string
        """
        extension = extension.lower()
        mime_type_map = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }
        return mime_type_map.get(extension, "application/octet-stream")

    @classmethod
    def merge_parsed_with_user_input(
        cls, parsed_data: Dict[str, Any], user_profile: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Merge parsed health report data with optional user input.

        User-provided data takes precedence over parsed data.
        This allows users to correct or supplement parsed information.

        Args:
            parsed_data: Data extracted from uploaded file
            user_profile: Optional user-provided data (age, gender, etc.)

        Returns:
            Merged health report dictionary with user inputs taking precedence
        """
        if not user_profile:
            return parsed_data

        merged = parsed_data.copy()

        # Add anthropometry from user if provided
        if "age" in user_profile:
            if "demographics" not in merged:
                merged["demographics"] = {}
            merged["demographics"]["age"] = user_profile["age"]

        if "gender" in user_profile:
            if "demographics" not in merged:
                merged["demographics"] = {}
            merged["demographics"]["gender"] = user_profile["gender"]

        # Add lifestyle preferences from user
        if "dietary_restrictions" in user_profile:
            if "lifestyle" not in merged:
                merged["lifestyle"] = {}
            merged["lifestyle"]["dietary_restrictions"] = user_profile[
                "dietary_restrictions"
            ]

        if "health_goal" in user_profile:
            if "lifestyle" not in merged:
                merged["lifestyle"] = {}
            merged["lifestyle"]["health_goal"] = user_profile["health_goal"]

        if "exercise_barriers" in user_profile:
            if "lifestyle" not in merged:
                merged["lifestyle"] = {}
            merged["lifestyle"]["exercise_barriers"] = user_profile[
                "exercise_barriers"
            ]

        logger.info(
            "Merged parsed data with user input",
            parsed_keys=list(parsed_data.keys()),
            user_keys=list(user_profile.keys()),
        )

        return merged

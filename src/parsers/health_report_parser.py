"""Unified health report parser for Health Action Squad.

Provides a single interface for parsing health reports from multiple formats:
- PDF files
- JPG/JPEG images
- PNG images

Features:
- Automatic file type detection
- Multi-page PDF support
- OCR-based text extraction using PaddleOCR
- Data completeness scoring (0.0-1.0)
- Intelligent data merging from multiple sources
- LLM fallback for incomplete extraction
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum
import base64

from pdf2image import convert_from_path
from PIL import Image

from ..utils.logger import get_logger, AgentLogger
from ..common.config import Config
from .llm_fallback import GeminiStructuredExtractor
from .simple_mobile_preprocessor import SimpleMobilePreprocessor

logger = get_logger(__name__)
agent_logger = AgentLogger("HealthReportParser")


class FileType(Enum):
    """Supported file types for health report parsing."""

    PDF = "pdf"
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    UNKNOWN = "unknown"


class HealthReportParser:
    """Unified interface for parsing health reports from multiple formats.

    Supports automatic file type detection, multi-page PDF handling,
    OCR extraction, and LLM-based fallback for incomplete data.

    Attributes:
        min_completeness_threshold: Minimum completeness score (0.0-1.0)
            to skip LLM fallback (default: 0.7)
        ocr_model: OCR model to use ('paddleocr' only, for now)
        required_fields: List of health metric fields expected in output
    """

    # Required health metric fields for completeness check
    REQUIRED_FIELDS = {
        "blood_pressure",
        "cholesterol",
        "glucose",
        "bmi",
        "heart_rate",
        "temperature",
        "oxygen_saturation",
    }

    def __init__(
        self,
        min_completeness_threshold: float = 0.7,
        use_llm_fallback: bool = True,
        preprocess_images: bool = True,
        session_id: Optional[str] = None,
    ):
        """Initialize health report parser.

        Args:
            min_completeness_threshold: Minimum completeness score (0.0-1.0)
                to skip LLM fallback (default: 0.7)
            use_llm_fallback: Whether to use LLM for incomplete data (default: True)
            preprocess_images: Whether to preprocess images for mobile photo quality (default: True)
            session_id: Optional session ID for logging context
        """
        self.min_completeness_threshold = min_completeness_threshold
        self.use_llm_fallback = use_llm_fallback
        self.preprocess_images = preprocess_images
        self.session_id = session_id
        self.llm_extractor = GeminiStructuredExtractor(session_id=session_id)
        self.image_preprocessor = SimpleMobilePreprocessor(enable_threshold=False) if preprocess_images else None

        if session_id:
            agent_logger.set_session(session_id)

    @staticmethod
    def _detect_file_type(file_path: str) -> FileType:
        """Detect file type from file extension.

        Args:
            file_path: Path to file

        Returns:
            FileType enum value

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = path.suffix.lower().lstrip(".")
        try:
            return FileType[extension.upper()]
        except KeyError:
            return FileType.UNKNOWN

    @staticmethod
    def _pdf_to_images(file_path: str) -> List[Image.Image]:
        """Convert PDF to list of PIL Image objects.

        Args:
            file_path: Path to PDF file

        Returns:
            List of PIL Image objects (one per page)

        Raises:
            Exception: If PDF conversion fails
        """
        try:
            agent_logger.info(
                "Converting PDF to images", file=file_path, action="pdf_to_images"
            )
            images = convert_from_path(file_path, dpi=300)
            agent_logger.info(
                "PDF conversion successful",
                file=file_path,
                page_count=len(images),
            )
            return images
        except Exception as e:
            agent_logger.error(
                "PDF conversion failed", file=file_path, error=str(e)
            )
            raise

    @staticmethod
    def _load_image(file_path: str) -> Image.Image:
        """Load image from file path.

        Args:
            file_path: Path to image file

        Returns:
            PIL Image object

        Raises:
            Exception: If image loading fails
        """
        try:
            agent_logger.info(
                "Loading image", file=file_path, action="load_image"
            )
            img = Image.open(file_path)
            agent_logger.info(
                "Image loaded successfully",
                file=file_path,
                size=img.size,
                format=img.format,
            )
            return img
        except Exception as e:
            agent_logger.error(
                "Image loading failed", file=file_path, error=str(e)
            )
            raise

    @staticmethod
    def _extract_from_ocr(images: List[Image.Image]) -> Tuple[Dict, float]:
        """Extract health data from images using PaddleOCR.

        Args:
            images: List of PIL Image objects

        Returns:
            Tuple of (extracted_data, completeness_score)
            - extracted_data: Dict with health metrics
            - completeness_score: Float between 0.0 and 1.0
        """
        agent_logger.info(
            "Extracting data from OCR",
            page_count=len(images),
            action="extract_from_ocr",
        )

        # Use PaddleOCRHealthReportParser for actual OCR extraction
        try:
            from .paddle_ocr_parser import PaddleOCRHealthReportParser
            import tempfile
            import asyncio

            # Create temporary directory for image files
            with tempfile.TemporaryDirectory() as temp_dir:
                extracted_data = {}
                all_vital_signs = {}
                patient_info = {}

                # Save images and process with PaddleOCR
                for idx, img in enumerate(images):
                    # Save PIL Image to temporary file
                    temp_img_path = Path(temp_dir) / f"page_{idx}.jpg"
                    img.save(str(temp_img_path), format="JPEG")

                    # Run OCR parser synchronously (PaddleOCR is not async)
                    # Use 'chinese_cht' for Traditional Chinese + English (台灣健康報告混合語言)
                    parser = PaddleOCRHealthReportParser(language="chinese_cht", device="cpu")

                    # Parse synchronously (we're already in a thread pool via asyncio.to_thread)
                    # Create event loop for async parse if needed
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    parsed_report = loop.run_until_complete(parser.parse(str(temp_img_path)))

                    # Merge patient info (keep first non-empty value)
                    if parsed_report.patient_info and not patient_info:
                        patient_info = parsed_report.patient_info

                    # Merge vital signs from all pages
                    for metric_name, metric_obj in parsed_report.vital_signs.items():
                        all_vital_signs[metric_name] = metric_obj

                # Convert vital signs to flat dictionary
                for metric_name, metric_obj in all_vital_signs.items():
                    extracted_data[metric_name] = metric_obj.value

                # Add patient info fields
                if "bmi" in patient_info:
                    extracted_data["bmi"] = patient_info["bmi"]
                if "weight_kg" in patient_info:
                    extracted_data["weight"] = patient_info["weight_kg"]
                if "height_cm" in patient_info:
                    extracted_data["height"] = patient_info["height_cm"]

                # Calculate completeness based on extracted fields
                required_fields = {
                    "blood_pressure", "cholesterol", "glucose", "bmi",
                    "heart_rate", "temperature", "oxygen_saturation"
                }

                # Map PaddleOCR field names to required fields
                field_mapping = {
                    "systolic_bp": "blood_pressure",
                    "total_cholesterol": "cholesterol",
                    "fasting_glucose": "glucose",
                }

                present_count = 0
                for req_field in required_fields:
                    # Check direct match or mapped field
                    if req_field in extracted_data:
                        present_count += 1
                    elif req_field in field_mapping.values():
                        # Check if any mapped field exists
                        for ocr_field, mapped in field_mapping.items():
                            if mapped == req_field and ocr_field in extracted_data:
                                present_count += 1
                                break

                completeness_score = present_count / len(required_fields) if required_fields else 0.0

                agent_logger.info(
                    "OCR extraction complete",
                    page_count=len(images),
                    completeness=completeness_score,
                    fields_extracted=len(extracted_data),
                )

                return extracted_data, completeness_score

        except Exception as e:
            agent_logger.error(
                "OCR extraction failed",
                error=str(e),
                page_count=len(images),
            )
            # Fallback to empty result
            return {}, 0.0

    def _check_completeness(self, data: Dict) -> float:
        """Check data completeness by counting present fields.

        Calculates a completeness score (0.0-1.0) based on the ratio of
        present health metrics to required fields.

        Args:
            data: Dictionary containing extracted health data

        Returns:
            Float between 0.0 and 1.0:
            - 0.0: No required fields present
            - 1.0: All required fields present
            - 0.5: 50% of required fields present

        Example:
            >>> parser = HealthReportParser()
            >>> score = parser._check_completeness({
            ...     "blood_pressure": "120/80",
            ...     "cholesterol": "200"
            ... })
            >>> # score = 2/7 ≈ 0.29
        """
        if not data:
            return 0.0

        # Count how many required fields are present and non-empty
        present_fields = sum(
            1 for field in self.REQUIRED_FIELDS
            if field in data and data[field] is not None
        )

        completeness = present_fields / len(self.REQUIRED_FIELDS)
        agent_logger.debug(
            "Completeness check",
            present_fields=present_fields,
            required_fields=len(self.REQUIRED_FIELDS),
            completeness_score=completeness,
        )
        return completeness

    @staticmethod
    def _merge_data(data1: Dict, data2: Dict) -> Dict:
        """Intelligently merge two health data dictionaries.

        Merging strategy:
        1. For each field in data1:
           - If data1[field] is not empty, keep it
           - If data1[field] is empty and data2 has it, use data2[field]
        2. Add any fields from data2 not in data1

        Args:
            data1: Primary data source (takes precedence)
            data2: Secondary data source (fallback)

        Returns:
            Merged dictionary with fields from both sources

        Example:
            >>> parser = HealthReportParser()
            >>> result = parser._merge_data(
            ...     {"blood_pressure": "120/80", "cholesterol": ""},
            ...     {"cholesterol": "200", "glucose": "100"}
            ... )
            >>> # Returns: {
            >>> #   "blood_pressure": "120/80",
            >>> #   "cholesterol": "200",
            >>> #   "glucose": "100"
            >>> # }
        """
        merged = data1.copy()

        for key, value in data2.items():
            if key not in merged or not merged[key]:
                merged[key] = value

        agent_logger.debug(
            "Data merge complete",
            data1_fields=len(data1),
            data2_fields=len(data2),
            merged_fields=len(merged),
        )
        return merged

    async def parse(
        self, file_path: str, use_llm_fallback: Optional[bool] = None
    ) -> Dict:
        """Parse health report from file and extract structured data.

        Main entry point for parsing. Automatically detects file type,
        extracts text/data, checks completeness, and optionally uses LLM
        fallback if extraction is incomplete.

        Args:
            file_path: Path to health report file (PDF, JPG, PNG)
            use_llm_fallback: Override instance setting for LLM fallback.
                If None, uses self.use_llm_fallback

        Returns:
            Dictionary containing:
            - 'data': Extracted health metrics
            - 'completeness': Float between 0.0 and 1.0
            - 'source': 'ocr', 'llm', or 'hybrid'
            - 'error': Error message if parsing failed (optional)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type not supported

        Example:
            >>> parser = HealthReportParser(session_id="session_123")
            >>> result = await parser.parse("health_report.pdf")
            >>> print(result['completeness'])
            >>> print(result['data'])
        """
        use_llm_fallback = (
            use_llm_fallback
            if use_llm_fallback is not None
            else self.use_llm_fallback
        )

        file_path_obj = Path(file_path)
        agent_logger.info(
            "Parsing started", file=str(file_path), action="parse_start"
        )

        try:
            # Step 1: Detect file type
            file_type = self._detect_file_type(file_path)
            agent_logger.info("File type detected", file_type=file_type.value)

            if file_type == FileType.UNKNOWN:
                raise ValueError(f"Unsupported file type: {file_path}")

            # Step 2: Load file and convert to images
            if file_type == FileType.PDF:
                images = self._pdf_to_images(file_path)
            elif file_type in (FileType.JPG, FileType.JPEG, FileType.PNG):
                images = [self._load_image(file_path)]
            else:
                raise ValueError(f"File type not handled: {file_type}")

            # Step 3: Preprocess images for mobile photo quality (if enabled)
            if self.preprocess_images and file_type in (FileType.JPG, FileType.JPEG, FileType.PNG):
                agent_logger.info("Preprocessing mobile photo for OCR optimization")
                # Run preprocessing in thread pool for true parallelism (CPU-intensive operation)
                processed_array = await asyncio.to_thread(
                    self.image_preprocessor.preprocess, file_path
                )
                # Convert numpy array back to PIL Image
                images = [Image.fromarray(processed_array)]
                agent_logger.info("Image preprocessing completed")

            # Step 4: Extract data using OCR
            # Run OCR in thread pool for true parallelism (CPU-intensive operation)
            ocr_data, ocr_completeness = await asyncio.to_thread(
                self._extract_from_ocr, images
            )
            agent_logger.info(
                "OCR extraction completed",
                completeness=ocr_completeness,
            )

            # Step 5: Check completeness
            completeness = self._check_completeness(ocr_data)
            source = "ocr"
            final_data = ocr_data

            # Step 6: LLM fallback if incomplete
            if (
                use_llm_fallback
                and completeness < self.min_completeness_threshold
            ):
                agent_logger.info(
                    "Activating LLM fallback",
                    ocr_completeness=completeness,
                    threshold=self.min_completeness_threshold,
                )

                try:
                    # Use first image or text representation for LLM
                    if images:
                        # For now, pass the file path to LLM extractor
                        # In production, could pass image directly
                        llm_data = await self.llm_extractor.extract(
                            file_path
                        )
                    else:
                        llm_data = {}

                    # Merge OCR data with LLM extraction (OCR takes priority)
                    final_data = self._merge_data(ocr_data, llm_data)
                    completeness = self._check_completeness(final_data)
                    source = "hybrid"

                    agent_logger.info(
                        "LLM fallback completed",
                        llm_completeness=completeness,
                        source=source,
                    )
                except Exception as e:
                    agent_logger.warning(
                        "LLM fallback failed, using OCR data only",
                        error=str(e),
                    )
                    source = "ocr"

            agent_logger.info(
                "Parsing completed successfully",
                file=str(file_path),
                source=source,
                completeness=completeness,
            )

            return {
                "data": final_data,
                "completeness": completeness,
                "source": source,
                "file_path": str(file_path),
                "file_type": file_type.value,
            }

        except Exception as e:
            agent_logger.error(
                "Parsing failed", file=str(file_path), error=str(e)
            )
            return {
                "data": {},
                "completeness": 0.0,
                "source": "error",
                "file_path": str(file_path),
                "error": str(e),
            }

    async def parse_batch(
        self, file_paths: List[str], merge_results: bool = True
    ) -> Dict:
        """Parse multiple health report files and optionally merge results.

        Args:
            file_paths: List of file paths to parse
            merge_results: Whether to merge results from all files (default: True)

        Returns:
            Dictionary containing:
            - 'results': List of parse results for each file
            - 'merged_data': Merged data if merge_results=True
            - 'overall_completeness': Aggregate completeness score

        Example:
            >>> parser = HealthReportParser()
            >>> result = await parser.parse_batch([
            ...     "report_page1.pdf",
            ...     "report_page2.pdf"
            ... ])
            >>> print(result['overall_completeness'])
        """
        agent_logger.info(
            "Batch parsing started",
            file_count=len(file_paths),
            merge=merge_results,
        )

        # Parse all files concurrently
        tasks = [self.parse(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks)

        merged_data = {}
        if merge_results:
            for result in results:
                if result["data"]:
                    merged_data = self._merge_data(merged_data, result["data"])

        overall_completeness = self._check_completeness(merged_data)

        agent_logger.info(
            "Batch parsing completed",
            file_count=len(file_paths),
            overall_completeness=overall_completeness,
        )

        return {
            "results": results,
            "merged_data": merged_data if merge_results else None,
            "overall_completeness": overall_completeness,
        }

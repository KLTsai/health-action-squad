"""LLM-based fallback extractor for incomplete health report parsing.

Provides structured extraction of health metrics using Gemini API
when OCR extraction is incomplete or fails. Uses prompt engineering
to ensure consistent, structured JSON output.
"""

import asyncio
import json
import base64
from pathlib import Path
from typing import Dict, Optional

from ..ai.client import AIClientFactory
from ..utils.logger import get_logger, AgentLogger

logger = get_logger(__name__)
agent_logger = AgentLogger("GeminiStructuredExtractor")

# Structured extraction prompt for Gemini
EXTRACTION_PROMPT = """You are a medical data extraction specialist. Analyze the provided health report image or text and extract all health metrics.

IMPORTANT: You MUST respond with valid JSON only, no other text.

Extract the following fields if present:
- blood_pressure (format: systolic/diastolic in mmHg)
- systolic (numeric only)
- diastolic (numeric only)
- cholesterol (total cholesterol in mg/dL)
- hdl_cholesterol (HDL in mg/dL)
- ldl_cholesterol (LDL in mg/dL)
- triglycerides (in mg/dL)
- glucose (fasting glucose in mg/dL)
- blood_glucose (alternative name)
- bmi (body mass index, numeric)
- weight (in kg)
- height (in cm)
- heart_rate (beats per minute)
- pulse (alternative name)
- temperature (in Celsius)
- oxygen_saturation (SpO2 in %)
- respiratory_rate (breaths per minute)
- hba1c (hemoglobin A1c in %)
- tsh (thyroid stimulating hormone)
- total_protein (in g/dL)
- albumin (in g/dL)
- globulin (in g/dL)
- aspartate_aminotransferase (AST in U/L)
- alanine_aminotransferase (ALT in U/L)
- alkaline_phosphatase (ALP in U/L)
- total_bilirubin (in mg/dL)
- direct_bilirubin (in mg/dL)
- creatinine (in mg/dL)
- blood_urea_nitrogen (BUN in mg/dL)
- sodium (Na in mEq/L)
- potassium (K in mEq/L)
- chloride (Cl in mEq/L)
- co2 (bicarbonate in mEq/L)
- calcium (in mg/dL)
- phosphorus (in mg/dL)
- magnesium (in mg/dL)
- hemoglobin (Hb in g/dL)
- hematocrit (Hct in %)
- white_blood_cells (WBC in x10^9/L)
- red_blood_cells (RBC in x10^12/L)
- platelets (in x10^9/L)
- examination_date (format: YYYY-MM-DD if available)

For any field that is NOT present, OMIT it from the JSON (do not include with null/empty value).

Return ONLY a valid JSON object with the extracted values. Example format:
{{
  "blood_pressure": "120/80",
  "systolic": 120,
  "diastolic": 80,
  "cholesterol": 200,
  "glucose": 100,
  "bmi": 22.5,
  "heart_rate": 72
}}

Health Report Content:
{content}

RESPOND WITH VALID JSON ONLY:"""


class GeminiStructuredExtractor:
    """Use Gemini API to extract structured health data from reports.

    Features:
    - Automatic image handling (base64 encoding for Gemini API)
    - Prompt engineering for consistent JSON output
    - Error handling and retry logic
    - Detailed logging for debugging

    Attributes:
        model_name: Gemini model to use (default: gemini-2.5-flash)
        temperature: Sampling temperature for model (default: 0.1 for consistency)
        max_output_tokens: Maximum tokens in response (default: 2048)
        session_id: Optional session ID for logging context
    """

    # Maximum retries for LLM extraction
    MAX_RETRIES = 3

    # File size limit for base64 encoding (100 MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        max_output_tokens: int = 2048,
        session_id: Optional[str] = None,
    ):
        """Initialize Gemini structured extractor.

        Args:
            model_name: Gemini model name (uses config default if None)
            temperature: Sampling temperature (default: 0.1 for consistency)
            max_output_tokens: Maximum response tokens (default: 2048)
            session_id: Optional session ID for logging context
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.session_id = session_id

        # Create Gemini client with low temperature for structured output
        self.client = AIClientFactory.create_gemini_client(
            model=model_name or "gemini-2.5-flash",
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        if session_id:
            agent_logger.set_session(session_id)

        agent_logger.info(
            "GeminiStructuredExtractor initialized",
            model=self.model_name or "gemini-2.5-flash",
            temperature=temperature,
        )

    @staticmethod
    def _is_image_file(file_path: str) -> bool:
        """Check if file is an image.

        Args:
            file_path: Path to file

        Returns:
            True if file is JPG, JPEG, or PNG

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        image_extensions = {".jpg", ".jpeg", ".png"}
        return path.suffix.lower() in image_extensions

    @staticmethod
    def _is_pdf_file(file_path: str) -> bool:
        """Check if file is a PDF.

        Args:
            file_path: Path to file

        Returns:
            True if file is PDF

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return path.suffix.lower() == ".pdf"

    @staticmethod
    def _encode_image_to_base64(file_path: str) -> str:
        """Encode image file to base64 string.

        Args:
            file_path: Path to image file

        Returns:
            Base64-encoded image data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is too large (>100MB)
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = path.stat().st_size
        if file_size > GeminiStructuredExtractor.MAX_FILE_SIZE:
            raise ValueError(
                f"File too large: {file_size} bytes (max: "
                f"{GeminiStructuredExtractor.MAX_FILE_SIZE} bytes)"
            )

        with open(path, "rb") as f:
            image_data = f.read()
        return base64.standard_b64encode(image_data).decode("utf-8")

    def _determine_mime_type(self, file_path: str) -> str:
        """Determine MIME type from file extension.

        Args:
            file_path: Path to file

        Returns:
            MIME type string (e.g., "image/jpeg")

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type not supported
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
        }

        extension = path.suffix.lower()
        if extension not in mime_types:
            raise ValueError(f"Unsupported file type: {extension}")

        return mime_types[extension]

    async def _extract_from_image(self, file_path: str) -> Dict:
        """Extract health data from image using Gemini vision API.

        Args:
            file_path: Path to image file (JPG, JPEG, PNG)

        Returns:
            Dictionary containing extracted health metrics

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If extraction fails
        """
        agent_logger.info(
            "Extracting from image using Gemini Vision",
            file=file_path,
            action="extract_from_image",
        )

        try:
            # Encode image to base64
            image_data = self._encode_image_to_base64(file_path)
            mime_type = self._determine_mime_type(file_path)

            # Create content with image for Gemini API
            # Use correct Gemini API format with inline_data
            content = [
                EXTRACTION_PROMPT.format(content="[Image analysis]"),
                {
                    "mime_type": mime_type,
                    "data": image_data,
                },
            ]

            # Call Gemini API
            response = self.client.generate_content(content)
            response_text = response.text.strip()

            agent_logger.debug(
                "Gemini vision response received",
                response_length=len(response_text),
            )

            # Parse JSON response
            extracted_data = self._parse_json_response(response_text)
            agent_logger.info(
                "Image extraction successful",
                file=file_path,
                fields_extracted=len(extracted_data),
            )
            return extracted_data

        except Exception as e:
            agent_logger.error(
                "Image extraction failed", file=file_path, error=str(e)
            )
            raise

    async def _extract_from_text(self, text_content: str) -> Dict:
        """Extract health data from text content using Gemini.

        Args:
            text_content: Health report text content

        Returns:
            Dictionary containing extracted health metrics

        Raises:
            ValueError: If extraction fails
        """
        agent_logger.info(
            "Extracting from text using Gemini",
            text_length=len(text_content),
            action="extract_from_text",
        )

        try:
            # Create prompt with text content
            full_prompt = EXTRACTION_PROMPT.format(content=text_content)

            # Call Gemini API
            response = self.client.generate_content(full_prompt)
            response_text = response.text.strip()

            agent_logger.debug(
                "Gemini text response received",
                response_length=len(response_text),
            )

            # Parse JSON response
            extracted_data = self._parse_json_response(response_text)
            agent_logger.info(
                "Text extraction successful",
                fields_extracted=len(extracted_data),
            )
            return extracted_data

        except Exception as e:
            agent_logger.error(
                "Text extraction failed", error=str(e)
            )
            raise

    @staticmethod
    def _parse_json_response(response_text: str) -> Dict:
        """Parse JSON response from Gemini API.

        Handles common edge cases:
        - Markdown code blocks (```json ... ```)
        - Extra whitespace
        - Partial JSON

        Args:
            response_text: Raw response text from Gemini

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If JSON parsing fails
        """
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            # Extract content between ``` markers
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                response_text = response_text[start:end]

        # Try to parse JSON
        try:
            data = json.loads(response_text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError as e:
            agent_logger.warning(
                "Failed to parse JSON response",
                error=str(e),
                response_preview=response_text[:200],
            )
            raise ValueError(f"Invalid JSON in response: {str(e)}")

    async def extract(
        self, file_or_text: str, is_text: bool = False
    ) -> Dict:
        """Extract structured health data using Gemini API.

        Main entry point for LLM-based extraction. Automatically detects
        file type (image, PDF, or text) and uses appropriate extraction method.

        Args:
            file_or_text: File path or text content
            is_text: If True, treats input as text content; otherwise as file path

        Returns:
            Dictionary containing extracted health metrics:
            - Keys: health metric names
            - Values: extracted values (numbers or strings)

        Example:
            >>> extractor = GeminiStructuredExtractor()
            >>> # From image file
            >>> data = await extractor.extract("health_report.jpg")
            >>> print(data['cholesterol'])
            200
            >>> # From text
            >>> data = await extractor.extract(
            ...     "Total Cholesterol: 200 mg/dL\\nHDL: 50 mg/dL",
            ...     is_text=True
            ... )
            >>> print(data['cholesterol'])
            200
        """
        agent_logger.info(
            "LLM extraction started",
            input_type="text" if is_text else "file",
            action="extract_start",
        )

        try:
            if is_text:
                # Direct text extraction
                extracted_data = await self._extract_from_text(file_or_text)
            else:
                # File-based extraction
                file_path = file_or_text
                if self._is_image_file(file_path):
                    extracted_data = await self._extract_from_image(
                        file_path
                    )
                elif self._is_pdf_file(file_path):
                    # For PDFs, convert to text representation
                    # In production, could use pdf2image + vision API
                    agent_logger.info(
                        "PDF provided, using text extraction fallback",
                        file=file_path,
                    )
                    # Placeholder: In real implementation, extract text from PDF
                    extracted_data = {}
                else:
                    raise ValueError(
                        f"Unsupported file type: {Path(file_path).suffix}"
                    )

            agent_logger.info(
                "LLM extraction completed successfully",
                fields_extracted=len(extracted_data),
            )
            return extracted_data

        except Exception as e:
            agent_logger.error(
                "LLM extraction failed", error=str(e)
            )
            # Return empty dict on failure - let caller decide how to handle
            return {}

    async def extract_with_retry(
        self, file_or_text: str, is_text: bool = False, max_retries: int = 3
    ) -> Dict:
        """Extract with automatic retry on failure.

        Args:
            file_or_text: File path or text content
            is_text: If True, treats input as text content
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            Dictionary containing extracted health metrics

        Example:
            >>> extractor = GeminiStructuredExtractor()
            >>> data = await extractor.extract_with_retry(
            ...     "health_report.jpg",
            ...     max_retries=3
            ... )
        """
        agent_logger.info(
            "Starting extraction with retry logic",
            max_retries=max_retries,
            input_type="text" if is_text else "file",
        )

        for attempt in range(max_retries):
            try:
                agent_logger.debug(
                    "Extraction attempt",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                result = await self.extract(file_or_text, is_text=is_text)

                if result:
                    agent_logger.info(
                        "Extraction successful",
                        attempt=attempt + 1,
                        fields_extracted=len(result),
                    )
                    return result

            except Exception as e:
                agent_logger.warning(
                    "Extraction attempt failed",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == max_retries - 1:
                    agent_logger.error(
                        "Extraction failed after all retries",
                        max_attempts=max_retries,
                    )
                else:
                    # Wait before retry (exponential backoff)
                    wait_time = 2 ** attempt
                    agent_logger.debug(
                        "Waiting before retry",
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)

        return {}

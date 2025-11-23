"""Unit tests for GeminiStructuredExtractor.

Tests cover:
- Image file detection and encoding
- JSON parsing
- Error handling
- Retry logic
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from src.parsers.llm_fallback import (
    GeminiStructuredExtractor,
    EXTRACTION_PROMPT,
)


class TestFileDetection:
    """Test file type detection methods."""

    def test_is_image_file_jpg(self, tmp_path):
        """Test JPG image detection."""
        jpg_file = tmp_path / "report.jpg"
        jpg_file.write_text("dummy")

        assert GeminiStructuredExtractor._is_image_file(str(jpg_file)) is True

    def test_is_image_file_jpeg(self, tmp_path):
        """Test JPEG image detection."""
        jpeg_file = tmp_path / "report.jpeg"
        jpeg_file.write_text("dummy")

        assert (
            GeminiStructuredExtractor._is_image_file(str(jpeg_file)) is True
        )

    def test_is_image_file_png(self, tmp_path):
        """Test PNG image detection."""
        png_file = tmp_path / "report.png"
        png_file.write_text("dummy")

        assert GeminiStructuredExtractor._is_image_file(str(png_file)) is True

    def test_is_image_file_pdf(self, tmp_path):
        """Test PDF is not an image."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_text("dummy")

        assert GeminiStructuredExtractor._is_image_file(str(pdf_file)) is False

    def test_is_pdf_file(self, tmp_path):
        """Test PDF detection."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_text("dummy")

        assert GeminiStructuredExtractor._is_pdf_file(str(pdf_file)) is True

    def test_is_pdf_file_jpg(self, tmp_path):
        """Test JPG is not a PDF."""
        jpg_file = tmp_path / "report.jpg"
        jpg_file.write_text("dummy")

        assert GeminiStructuredExtractor._is_pdf_file(str(jpg_file)) is False

    def test_file_detection_nonexistent(self):
        """Test error on nonexistent file."""
        with pytest.raises(FileNotFoundError):
            GeminiStructuredExtractor._is_image_file("/nonexistent/file.jpg")


class TestImageEncoding:
    """Test image base64 encoding."""

    def test_encode_image_to_base64(self, tmp_path):
        """Test successful base64 encoding."""
        image_file = tmp_path / "test.jpg"
        image_file.write_bytes(b"fake image data")

        encoded = GeminiStructuredExtractor._encode_image_to_base64(
            str(image_file)
        )

        # Base64 string should be decodable
        import base64

        decoded = base64.b64decode(encoded)
        assert decoded == b"fake image data"

    def test_encode_nonexistent_file(self):
        """Test error on nonexistent file."""
        with pytest.raises(FileNotFoundError):
            GeminiStructuredExtractor._encode_image_to_base64(
                "/nonexistent/file.jpg"
            )

    def test_encode_file_too_large(self, tmp_path):
        """Test error on file exceeding size limit."""
        large_file = tmp_path / "large.jpg"
        # Create file larger than 100MB (the limit)
        # For testing, we'll just mock the file size check
        large_file.write_text("x" * 100)

        with patch(
            "src.parsers.llm_fallback.GeminiStructuredExtractor.MAX_FILE_SIZE",
            10,  # Set limit to 10 bytes
        ):
            with pytest.raises(ValueError, match="File too large"):
                GeminiStructuredExtractor._encode_image_to_base64(
                    str(large_file)
                )


class TestMimeTypeDetermination:
    """Test MIME type detection."""

    def test_mime_type_jpg(self, tmp_path):
        """Test MIME type for JPG."""
        jpg_file = tmp_path / "report.jpg"
        jpg_file.write_text("dummy")

        extractor = GeminiStructuredExtractor()
        mime_type = extractor._determine_mime_type(str(jpg_file))
        assert mime_type == "image/jpeg"

    def test_mime_type_jpeg(self, tmp_path):
        """Test MIME type for JPEG."""
        jpeg_file = tmp_path / "report.jpeg"
        jpeg_file.write_text("dummy")

        extractor = GeminiStructuredExtractor()
        mime_type = extractor._determine_mime_type(str(jpeg_file))
        assert mime_type == "image/jpeg"

    def test_mime_type_png(self, tmp_path):
        """Test MIME type for PNG."""
        png_file = tmp_path / "report.png"
        png_file.write_text("dummy")

        extractor = GeminiStructuredExtractor()
        mime_type = extractor._determine_mime_type(str(png_file))
        assert mime_type == "image/png"

    def test_mime_type_pdf(self, tmp_path):
        """Test MIME type for PDF."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_text("dummy")

        extractor = GeminiStructuredExtractor()
        mime_type = extractor._determine_mime_type(str(pdf_file))
        assert mime_type == "application/pdf"

    def test_mime_type_unsupported(self, tmp_path):
        """Test error on unsupported file type."""
        unknown_file = tmp_path / "report.xyz"
        unknown_file.write_text("dummy")

        extractor = GeminiStructuredExtractor()
        with pytest.raises(ValueError, match="Unsupported file type"):
            extractor._determine_mime_type(str(unknown_file))


class TestJsonParsing:
    """Test JSON response parsing."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        json_str = '{"cholesterol": 200, "glucose": 100}'
        result = GeminiStructuredExtractor._parse_json_response(json_str)

        assert result["cholesterol"] == 200
        assert result["glucose"] == 100

    def test_parse_json_with_markdown_code_block(self):
        """Test parsing JSON from markdown code block."""
        json_str = """```json
        {
            "cholesterol": 200,
            "glucose": 100
        }
        ```"""
        result = GeminiStructuredExtractor._parse_json_response(json_str)

        assert result["cholesterol"] == 200
        assert result["glucose"] == 100

    def test_parse_json_with_extra_whitespace(self):
        """Test parsing JSON with extra whitespace."""
        json_str = """
        {
            "cholesterol": 200,
            "glucose": 100
        }
        """
        result = GeminiStructuredExtractor._parse_json_response(json_str)

        assert result["cholesterol"] == 200
        assert result["glucose"] == 100

    def test_parse_invalid_json(self):
        """Test error on invalid JSON."""
        invalid_json = "{invalid json}"

        with pytest.raises(ValueError, match="Invalid JSON"):
            GeminiStructuredExtractor._parse_json_response(invalid_json)

    def test_parse_json_returns_dict(self):
        """Test that non-dict JSON is converted to empty dict."""
        json_str = '["item1", "item2"]'  # Array, not object
        result = GeminiStructuredExtractor._parse_json_response(json_str)

        assert result == {}

    def test_parse_empty_json_object(self):
        """Test parsing empty JSON object."""
        json_str = "{}"
        result = GeminiStructuredExtractor._parse_json_response(json_str)

        assert result == {}


class TestExtractorInitialization:
    """Test extractor initialization."""

    @patch("src.parsers.llm_fallback.AIClientFactory")
    def test_init_with_defaults(self, mock_factory):
        """Test initialization with default parameters."""
        mock_factory.create_gemini_client.return_value = MagicMock()

        extractor = GeminiStructuredExtractor()

        assert extractor.temperature == 0.1
        assert extractor.max_output_tokens == 2048
        assert extractor.session_id is None

    @patch("src.parsers.llm_fallback.AIClientFactory")
    def test_init_with_custom_model(self, mock_factory):
        """Test initialization with custom model name."""
        mock_factory.create_gemini_client.return_value = MagicMock()

        extractor = GeminiStructuredExtractor(model_name="custom-model")

        assert extractor.model_name == "custom-model"
        mock_factory.create_gemini_client.assert_called_once()
        call_args = mock_factory.create_gemini_client.call_args
        assert call_args.kwargs["model"] == "custom-model"

    @patch("src.parsers.llm_fallback.AIClientFactory")
    def test_init_with_session_id(self, mock_factory):
        """Test initialization with session ID."""
        mock_factory.create_gemini_client.return_value = MagicMock()

        extractor = GeminiStructuredExtractor(session_id="test_session")

        assert extractor.session_id == "test_session"


class TestExtraction:
    """Test LLM-based extraction."""

    @pytest.mark.asyncio
    @patch("src.parsers.llm_fallback.AIClientFactory")
    async def test_extract_text(self, mock_factory):
        """Test text extraction."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = '{"cholesterol": 200, "glucose": 100}'
        mock_client.generate_content.return_value = mock_response
        mock_factory.create_gemini_client.return_value = mock_client

        extractor = GeminiStructuredExtractor()
        result = await extractor.extract(
            "Total Cholesterol: 200 mg/dL", is_text=True
        )

        assert result["cholesterol"] == 200
        assert result["glucose"] == 100

    @pytest.mark.asyncio
    @patch("src.parsers.llm_fallback.AIClientFactory")
    async def test_extract_invalid_response(self, mock_factory):
        """Test extraction with invalid response."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "invalid json"
        mock_client.generate_content.return_value = mock_response
        mock_factory.create_gemini_client.return_value = mock_client

        extractor = GeminiStructuredExtractor()
        result = await extractor.extract(
            "Health data text", is_text=True
        )

        assert result == {}  # Should return empty dict on parse error

    @pytest.mark.asyncio
    @patch("src.parsers.llm_fallback.AIClientFactory")
    async def test_extract_with_retry_success(self, mock_factory):
        """Test extraction with retry on success."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = '{"cholesterol": 200}'
        mock_client.generate_content.return_value = mock_response
        mock_factory.create_gemini_client.return_value = mock_client

        extractor = GeminiStructuredExtractor()
        result = await extractor.extract_with_retry(
            "Health data", is_text=True, max_retries=3
        )

        assert result["cholesterol"] == 200
        # Should only call once since first attempt succeeds
        assert mock_client.generate_content.call_count == 1

    @pytest.mark.asyncio
    @patch("src.parsers.llm_fallback.AIClientFactory")
    async def test_extract_with_retry_all_fail(self, mock_factory):
        """Test extraction with retry when all attempts fail."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "invalid json"
        mock_client.generate_content.return_value = mock_response
        mock_factory.create_gemini_client.return_value = mock_client

        extractor = GeminiStructuredExtractor()
        result = await extractor.extract_with_retry(
            "Health data", is_text=True, max_retries=2
        )

        assert result == {}  # Should return empty dict after all retries fail
        # Should have retried max_retries times
        assert mock_client.generate_content.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

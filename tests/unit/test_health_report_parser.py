"""Unit tests for HealthReportParser.

Tests cover:
- File type detection
- Completeness scoring
- Data merging
- Error handling
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.parsers.health_report_parser import (
    HealthReportParser,
    FileType,
)


class TestFileTypeDetection:
    """Test file type detection functionality."""

    def test_detect_pdf(self, tmp_path):
        """Test PDF file detection."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_text("dummy")

        file_type = HealthReportParser._detect_file_type(str(pdf_file))
        assert file_type == FileType.PDF

    def test_detect_jpg(self, tmp_path):
        """Test JPG file detection."""
        jpg_file = tmp_path / "report.jpg"
        jpg_file.write_text("dummy")

        file_type = HealthReportParser._detect_file_type(str(jpg_file))
        assert file_type == FileType.JPG

    def test_detect_jpeg(self, tmp_path):
        """Test JPEG file detection."""
        jpeg_file = tmp_path / "report.jpeg"
        jpeg_file.write_text("dummy")

        file_type = HealthReportParser._detect_file_type(str(jpeg_file))
        assert file_type == FileType.JPEG

    def test_detect_png(self, tmp_path):
        """Test PNG file detection."""
        png_file = tmp_path / "report.png"
        png_file.write_text("dummy")

        file_type = HealthReportParser._detect_file_type(str(png_file))
        assert file_type == FileType.PNG

    def test_detect_unknown(self, tmp_path):
        """Test unknown file type detection."""
        unknown_file = tmp_path / "report.txt"
        unknown_file.write_text("dummy")

        file_type = HealthReportParser._detect_file_type(str(unknown_file))
        assert file_type == FileType.UNKNOWN

    def test_detect_nonexistent_file(self):
        """Test error on nonexistent file."""
        with pytest.raises(FileNotFoundError):
            HealthReportParser._detect_file_type("/nonexistent/file.pdf")


class TestCompletenessScoring:
    """Test data completeness scoring."""

    def test_empty_data(self):
        """Test completeness of empty data."""
        parser = HealthReportParser()
        score = parser._check_completeness({})
        assert score == 0.0

    def test_partial_data(self):
        """Test completeness with some fields."""
        parser = HealthReportParser()
        data = {
            "blood_pressure": "120/80",
            "cholesterol": "200",
            "glucose": "100",
        }
        # 3 out of 7 required fields
        score = parser._check_completeness(data)
        assert score == pytest.approx(3 / 7, rel=0.01)

    def test_complete_data(self):
        """Test completeness with all fields."""
        parser = HealthReportParser()
        data = {
            "blood_pressure": "120/80",
            "cholesterol": "200",
            "glucose": "100",
            "bmi": "22.5",
            "heart_rate": "72",
            "temperature": "37.0",
            "oxygen_saturation": "98",
        }
        score = parser._check_completeness(data)
        assert score == 1.0

    def test_empty_field_values(self):
        """Test that empty field values are not counted."""
        parser = HealthReportParser()
        data = {
            "blood_pressure": "120/80",
            "cholesterol": "",  # Empty
            "glucose": None,  # None
            "bmi": "22.5",
        }
        # Only 2 non-empty fields
        score = parser._check_completeness(data)
        assert score == pytest.approx(2 / 7, rel=0.01)


class TestDataMerging:
    """Test intelligent data merging functionality."""

    def test_merge_complementary_data(self):
        """Test merging of complementary data sources."""
        parser = HealthReportParser()
        data1 = {
            "blood_pressure": "120/80",
            "cholesterol": "",
        }
        data2 = {
            "cholesterol": "200",
            "glucose": "100",
        }
        merged = parser._merge_data(data1, data2)

        assert merged["blood_pressure"] == "120/80"
        assert merged["cholesterol"] == "200"
        assert merged["glucose"] == "100"

    def test_merge_data1_takes_priority(self):
        """Test that data1 takes priority when both have values."""
        parser = HealthReportParser()
        data1 = {"blood_pressure": "120/80"}
        data2 = {"blood_pressure": "110/70"}

        merged = parser._merge_data(data1, data2)
        assert merged["blood_pressure"] == "120/80"

    def test_merge_empty_data(self):
        """Test merging with empty data."""
        parser = HealthReportParser()
        data1 = {}
        data2 = {"cholesterol": "200"}

        merged = parser._merge_data(data1, data2)
        assert merged["cholesterol"] == "200"

    def test_merge_preserves_all_fields(self):
        """Test that merge preserves all fields from both sources."""
        parser = HealthReportParser()
        data1 = {"field1": "value1", "field2": ""}
        data2 = {"field2": "value2", "field3": "value3"}

        merged = parser._merge_data(data1, data2)
        assert "field1" in merged
        assert "field2" in merged
        assert "field3" in merged


class TestParserInitialization:
    """Test parser initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        parser = HealthReportParser()
        assert parser.min_completeness_threshold == 0.7
        assert parser.use_llm_fallback is True
        assert parser.session_id is None

    def test_init_with_custom_threshold(self):
        """Test initialization with custom threshold."""
        parser = HealthReportParser(min_completeness_threshold=0.5)
        assert parser.min_completeness_threshold == 0.5

    def test_init_with_session_id(self):
        """Test initialization with session ID."""
        parser = HealthReportParser(session_id="test_session_123")
        assert parser.session_id == "test_session_123"

    def test_init_without_llm_fallback(self):
        """Test initialization without LLM fallback."""
        parser = HealthReportParser(use_llm_fallback=False)
        assert parser.use_llm_fallback is False


class TestParsing:
    """Test main parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file."""
        parser = HealthReportParser()
        result = await parser.parse("/nonexistent/file.pdf")

        assert result["data"] == {}
        assert result["completeness"] == 0.0
        assert result["source"] == "error"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_parse_unsupported_file_type(self, tmp_path):
        """Test parsing unsupported file type."""
        unsupported_file = tmp_path / "report.txt"
        unsupported_file.write_text("dummy")

        parser = HealthReportParser()
        result = await parser.parse(str(unsupported_file))

        assert result["source"] == "error"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_parse_with_llm_fallback_override(self, tmp_path):
        """Test overriding LLM fallback setting."""
        image_file = tmp_path / "report.jpg"
        image_file.write_text("dummy")

        parser = HealthReportParser(use_llm_fallback=True)

        # Override to disable fallback
        result = await parser.parse(str(image_file), use_llm_fallback=False)

        # Should use OCR only (which will be empty due to mocking)
        assert result["source"] in ("ocr", "error")


class TestBatchParsing:
    """Test batch parsing functionality."""

    @pytest.mark.asyncio
    async def test_batch_parse_empty_list(self):
        """Test batch parsing with empty file list."""
        parser = HealthReportParser()
        result = await parser.parse_batch([])

        assert result["results"] == []
        assert result["overall_completeness"] == 0.0

    @pytest.mark.asyncio
    async def test_batch_parse_with_merge(self, tmp_path):
        """Test batch parsing with result merging."""
        file1 = tmp_path / "report1.jpg"
        file1.write_text("dummy")
        file2 = tmp_path / "report2.jpg"
        file2.write_text("dummy")

        parser = HealthReportParser()
        result = await parser.parse_batch(
            [str(file1), str(file2)], merge_results=True
        )

        assert len(result["results"]) == 2
        assert result["merged_data"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

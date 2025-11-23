"""Integration tests for parser components.

Tests the full parsing pipeline including:
- File handling
- OCR extraction
- LLM fallback
- Data merging
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.parsers import HealthReportParser, GeminiStructuredExtractor


class TestParserIntegration:
    """Integration tests for HealthReportParser."""

    @pytest.mark.asyncio
    async def test_parse_with_high_completeness_no_fallback(
        self, tmp_path
    ):
        """Test parsing with high completeness (>70%) skips LLM fallback."""
        # Create a dummy image file
        image_file = tmp_path / "health_report.jpg"
        image_file.write_bytes(b"fake jpg data")

        parser = HealthReportParser(
            min_completeness_threshold=0.7, use_llm_fallback=True
        )

        # Mock OCR extraction to return data with >70% completeness
        with patch.object(
            parser, "_extract_from_ocr"
        ) as mock_ocr:
            # Return data with 6 out of 7 required fields (85% complete)
            complete_data = {
                "blood_pressure": "120/80",
                "cholesterol": "200",
                "glucose": "100",
                "bmi": "22.5",
                "heart_rate": "72",
                "temperature": "37.0",
            }
            mock_ocr.return_value = (complete_data, 6 / 7)

            # Mock LLM extractor to verify it's NOT called
            with patch.object(
                parser.llm_extractor, "extract"
            ) as mock_llm:
                result = await parser.parse(str(image_file))

                # OCR completeness should be > 70%
                assert result["completeness"] > 0.7

                # LLM should NOT have been called
                mock_llm.assert_not_called()

                # Source should be 'ocr' only
                assert result["source"] == "ocr"

    @pytest.mark.asyncio
    async def test_parse_with_low_completeness_activates_fallback(
        self, tmp_path
    ):
        """Test parsing with low completeness (<70%) activates LLM fallback."""
        image_file = tmp_path / "health_report.jpg"
        image_file.write_bytes(b"fake jpg data")

        parser = HealthReportParser(
            min_completeness_threshold=0.7, use_llm_fallback=True
        )

        # Mock OCR extraction to return incomplete data (<70% complete)
        with patch.object(
            parser, "_extract_from_ocr"
        ) as mock_ocr:
            # Return data with 2 out of 7 required fields (28% complete)
            incomplete_data = {
                "blood_pressure": "120/80",
                "cholesterol": "200",
            }
            mock_ocr.return_value = (incomplete_data, 2 / 7)

            # Mock LLM extractor to return additional data
            with patch.object(
                parser.llm_extractor, "extract", new_callable=AsyncMock
            ) as mock_llm:
                llm_data = {
                    "glucose": "100",
                    "bmi": "22.5",
                }
                mock_llm.return_value = llm_data

                result = await parser.parse(str(image_file))

                # LLM should have been called
                mock_llm.assert_called_once()

                # Final data should be merged from both sources
                assert "blood_pressure" in result["data"]
                assert "glucose" in result["data"]

                # Source should be 'hybrid'
                assert result["source"] == "hybrid"

    @pytest.mark.asyncio
    async def test_parse_batch_multiple_files(self, tmp_path):
        """Test batch parsing of multiple files."""
        # Create multiple dummy files
        file1 = tmp_path / "report1.jpg"
        file1.write_bytes(b"fake jpg 1")
        file2 = tmp_path / "report2.jpg"
        file2.write_bytes(b"fake jpg 2")

        parser = HealthReportParser()

        # Mock OCR to return different data for each file
        with patch.object(
            parser, "_extract_from_ocr"
        ) as mock_ocr:
            data1 = {
                "blood_pressure": "120/80",
                "cholesterol": "200",
            }
            data2 = {
                "glucose": "100",
                "bmi": "22.5",
            }

            # Return different data for each call
            mock_ocr.side_effect = [
                (data1, 2 / 7),  # First file
                (data2, 2 / 7),  # Second file
            ]

            result = await parser.parse_batch(
                [str(file1), str(file2)], merge_results=True
            )

            # Should have results for both files
            assert len(result["results"]) == 2

            # Merged data should contain fields from both files
            assert result["merged_data"] is not None
            assert "blood_pressure" in result["merged_data"]
            assert "glucose" in result["merged_data"]


class TestLLMExtractorIntegration:
    """Integration tests for GeminiStructuredExtractor."""

    @pytest.mark.asyncio
    async def test_extract_image_with_gemini(self):
        """Test image extraction with Gemini API mock."""
        with patch(
            "src.parsers.llm_fallback.AIClientFactory"
        ) as mock_factory:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.text = '{"cholesterol": 200, "glucose": 100}'
            mock_client.generate_content.return_value = mock_response
            mock_factory.create_gemini_client.return_value = mock_client

            extractor = GeminiStructuredExtractor()

            # Create a temporary image file
            import tempfile

            with tempfile.NamedTemporaryFile(
                suffix=".jpg", delete=False
            ) as tmp:
                tmp.write(b"fake jpg data")
                tmp_path = tmp.name

            try:
                result = await extractor.extract(tmp_path)

                # Verify Gemini API was called
                mock_client.generate_content.assert_called_once()

                # Verify extracted data
                assert result["cholesterol"] == 200
                assert result["glucose"] == 100
            finally:
                Path(tmp_path).unlink()

    @pytest.mark.asyncio
    async def test_extract_with_retry_recovers_from_failure(self):
        """Test retry logic recovers from temporary failures."""
        with patch(
            "src.parsers.llm_fallback.AIClientFactory"
        ) as mock_factory:
            mock_client = AsyncMock()
            mock_response = MagicMock()

            # First call fails, second call succeeds
            mock_response.text = '{"cholesterol": 200}'
            mock_client.generate_content.side_effect = [
                Exception("API error"),  # First call fails
                mock_response,  # Second call succeeds
            ]
            mock_factory.create_gemini_client.return_value = mock_client

            extractor = GeminiStructuredExtractor()

            # Use direct text extraction to test retry
            # Note: extract() catches exceptions, so we test extract_with_retry
            result = await extractor.extract_with_retry(
                "Health report text", is_text=True, max_retries=2
            )

            # Should eventually succeed
            assert result.get("cholesterol") == 200


class TestDataMergingPipeline:
    """Integration tests for data merging functionality."""

    def test_merge_multiple_sources_sequential(self):
        """Test merging data from multiple sequential sources."""
        parser = HealthReportParser()

        # Simulate parsing from 3 different sources
        data_source1 = {"blood_pressure": "120/80"}
        data_source2 = {"cholesterol": "200", "glucose": "100"}
        data_source3 = {"bmi": "22.5", "heart_rate": "72"}

        # Merge sequentially
        merged = data_source1.copy()
        merged = parser._merge_data(merged, data_source2)
        merged = parser._merge_data(merged, data_source3)

        # All fields should be present
        assert merged["blood_pressure"] == "120/80"
        assert merged["cholesterol"] == "200"
        assert merged["glucose"] == "100"
        assert merged["bmi"] == "22.5"
        assert merged["heart_rate"] == "72"

        # Completeness should reflect all merged data
        completeness = parser._check_completeness(merged)
        assert completeness == 5 / 7  # 5 out of 7 required fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

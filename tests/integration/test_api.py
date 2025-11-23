"""Integration tests for FastAPI server."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.api.server import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_check_endpoint(self, client):
        """Test /health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data
        assert "model" in data
        assert "uptime_seconds" in data

    def test_api_v1_health_endpoint(self, client):
        """Test /api/v1/health endpoint (alias)."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestPlanGenerationEndpoint:
    """Test suite for plan generation endpoint."""

    def test_generate_plan_requires_health_report(self, client):
        """Test that /api/v1/generate_plan requires health_report field."""
        response = client.post("/api/v1/generate_plan", json={})

        # Should return 422 for missing required field
        assert response.status_code == 422

    def test_generate_plan_with_valid_data(self, client, sample_health_report, mock_adk_workflow_run):
        """Test /api/v1/generate_plan with valid health report."""
        # Mock the orchestrator.execute() method
        mock_result = {
            "session_id": "test-session-123",
            "status": "approved",
            "plan": "# Test Plan",
            "risk_tags": ["high_cholesterol"],
            "iterations": 1,
            "timestamp": "2025-11-21T10:00:00",
        }

        with patch('src.api.server.Orchestrator') as MockOrchestrator:
            mock_orchestrator_instance = MockOrchestrator.return_value
            mock_orchestrator_instance.execute = AsyncMock(return_value=mock_result)

            response = client.post(
                "/api/v1/generate_plan",
                json={"health_report": sample_health_report}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session-123"
            assert data["status"] == "approved"
            assert "plan" in data

    def test_generate_plan_with_user_profile(self, client, sample_health_report, sample_user_profile):
        """Test /api/v1/generate_plan with health report and user profile."""
        mock_result = {
            "session_id": "test-session-456",
            "status": "approved",
            "plan": "# Test Plan with Profile",
            "risk_tags": [],
            "iterations": 1,
            "timestamp": "2025-11-21T10:00:00",
        }

        with patch('src.api.server.Orchestrator') as MockOrchestrator:
            mock_orchestrator_instance = MockOrchestrator.return_value
            mock_orchestrator_instance.execute = AsyncMock(return_value=mock_result)

            response = client.post(
                "/api/v1/generate_plan",
                json={
                    "health_report": sample_health_report,
                    "user_profile": sample_user_profile
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert "plan" in data


class TestAPIDocumentation:
    """Test suite for API documentation endpoints."""

    def test_openapi_json_available(self, client):
        """Test that OpenAPI JSON is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Health Action Squad API"

    def test_swagger_ui_available(self, client):
        """Test that Swagger UI is available."""
        response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_available(self, client):
        """Test that ReDoc is available."""
        response = client.get("/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestMultiFileUploadEndpoint:
    """Test suite for multi-file upload endpoint."""

    def test_single_file_upload_still_works(self, client, tmp_path):
        """Test backward compatibility - single file upload should still work."""
        # Create a dummy PDF file
        test_file = tmp_path / "report.pdf"
        test_file.write_bytes(b"%PDF-1.4\n%dummy content for testing")

        # Mock the parser and orchestrator
        mock_parse_result = {
            "merged_data": {"total_cholesterol": 220, "ldl": 150},
            "overall_completeness": 0.85,
            "results": [{"source": "ocr"}],
        }

        mock_orchestrator_result = {
            "session_id": "test-session-single",
            "status": "approved",
            "plan": "# Test Plan",
            "risk_tags": ["high_cholesterol"],
            "iterations": 1,
            "timestamp": "2025-11-23T10:00:00",
        }

        with patch(
            "src.api.server.OCRParser"
        ) as MockParser, patch(
            "src.api.server.Orchestrator"
        ) as MockOrchestrator:
            # Mock parser
            mock_parser_instance = MockParser.return_value
            mock_parser_instance.parse_batch = AsyncMock(return_value=mock_parse_result)

            # Mock orchestrator
            mock_orchestrator_instance = MockOrchestrator.return_value
            mock_orchestrator_instance.execute = AsyncMock(
                return_value=mock_orchestrator_result
            )

            # Upload single file
            with open(test_file, "rb") as f:
                response = client.post(
                    "/api/v1/upload_report",
                    files=[("files", ("report.pdf", f, "application/pdf"))],
                    data={"age": 45, "gender": "male"},
                )

            assert response.status_code == 200
            data = response.json()
            assert "upload_stats" in data
            assert data["upload_stats"]["total_files"] == 1
            assert data["upload_stats"]["successfully_parsed"] == 1
            assert data["session_id"] == "test-session-single"

    def test_multi_file_upload_success(self, client, tmp_path):
        """Test successful multi-file upload with 3 pages."""
        # Create 3 dummy PDF files
        files = []
        for i in range(1, 4):
            test_file = tmp_path / f"page{i}.pdf"
            test_file.write_bytes(f"%PDF-1.4\npage {i} content".encode())
            files.append(test_file)

        # Mock parser response (merged data from 3 files)
        mock_parse_result = {
            "merged_data": {
                "total_cholesterol": 240,
                "ldl": 160,
                "hdl": 35,
                "blood_pressure_systolic": 140,
                "blood_pressure_diastolic": 90,
            },
            "overall_completeness": 0.9,
            "results": [
                {"source": "ocr"},
                {"source": "ocr"},
                {"source": "hybrid"},
            ],
        }

        mock_orchestrator_result = {
            "session_id": "test-session-multi",
            "status": "approved",
            "plan": "# Comprehensive Test Plan",
            "risk_tags": ["high_cholesterol", "elevated_blood_pressure"],
            "iterations": 1,
            "timestamp": "2025-11-23T10:00:00",
        }

        with patch(
            "src.api.server.OCRParser"
        ) as MockParser, patch(
            "src.api.server.Orchestrator"
        ) as MockOrchestrator:
            # Mock parser
            mock_parser_instance = MockParser.return_value
            mock_parser_instance.parse_batch = AsyncMock(return_value=mock_parse_result)

            # Mock orchestrator
            mock_orchestrator_instance = MockOrchestrator.return_value
            mock_orchestrator_instance.execute = AsyncMock(
                return_value=mock_orchestrator_result
            )

            # Upload 3 files
            file_handles = [open(f, "rb") for f in files]
            try:
                response = client.post(
                    "/api/v1/upload_report",
                    files=[
                        ("files", (f"page{i}.pdf", file_handles[i - 1], "application/pdf"))
                        for i in range(1, 4)
                    ],
                    data={"age": 50, "gender": "female", "health_goal": "Lower cholesterol"},
                )
            finally:
                for fh in file_handles:
                    fh.close()

            assert response.status_code == 200
            data = response.json()

            # Verify upload stats
            assert "upload_stats" in data
            assert data["upload_stats"]["total_files"] == 3
            assert data["upload_stats"]["successfully_parsed"] == 3
            assert data["upload_stats"]["failed_files"] == []
            assert "parsing_time_seconds" in data["upload_stats"]

            # Verify parsed data includes merged results
            assert "parsed_data" in data
            assert data["parsed_data"]["total_cholesterol"] == 240

    def test_multi_file_exceeds_max_files(self, client, tmp_path):
        """Test rejection when file count exceeds limit (10 files)."""
        # Create 11 files (exceeds limit)
        files = []
        for i in range(11):
            test_file = tmp_path / f"page{i}.pdf"
            test_file.write_bytes(b"%PDF-1.4\n%content")
            files.append(test_file)

        file_handles = [open(f, "rb") for f in files]
        try:
            response = client.post(
                "/api/v1/upload_report",
                files=[
                    ("files", (f"page{i}.pdf", file_handles[i], "application/pdf"))
                    for i in range(11)
                ],
            )
        finally:
            for fh in file_handles:
                fh.close()

        assert response.status_code == 400
        data = response.json()
        assert "Too many files" in data["detail"]["detail"]

    def test_multi_file_partial_success(self, client, tmp_path):
        """Test partial success when some files fail validation."""
        # Create 2 valid PDFs and 1 invalid file
        valid1 = tmp_path / "page1.pdf"
        valid2 = tmp_path / "page2.pdf"
        invalid = tmp_path / "badfile.txt"

        valid1.write_bytes(b"%PDF-1.4\n%content1")
        valid2.write_bytes(b"%PDF-1.4\n%content2")
        invalid.write_bytes(b"not a pdf file")

        # Mock parser response (only 2 valid files parsed)
        mock_parse_result = {
            "merged_data": {"total_cholesterol": 220},
            "overall_completeness": 0.7,
            "results": [{"source": "ocr"}, {"source": "ocr"}],
        }

        mock_orchestrator_result = {
            "session_id": "test-session-partial",
            "status": "approved",
            "plan": "# Partial Data Plan",
            "risk_tags": [],
            "iterations": 1,
            "timestamp": "2025-11-23T10:00:00",
        }

        with patch(
            "src.api.server.OCRParser"
        ) as MockParser, patch(
            "src.api.server.Orchestrator"
        ) as MockOrchestrator, patch(
            "src.api.server.LegacyParser.validate_file"
        ) as MockValidate:
            # Mock validation (valid1 and valid2 pass, invalid fails)
            def validate_side_effect(path):
                if "badfile" in str(path):
                    return {"valid": False, "error": "Invalid file format"}
                return {"valid": True}

            MockValidate.side_effect = validate_side_effect

            # Mock parser
            mock_parser_instance = MockParser.return_value
            mock_parser_instance.parse_batch = AsyncMock(return_value=mock_parse_result)

            # Mock orchestrator
            mock_orchestrator_instance = MockOrchestrator.return_value
            mock_orchestrator_instance.execute = AsyncMock(
                return_value=mock_orchestrator_result
            )

            # Upload 3 files (2 valid, 1 invalid)
            with open(valid1, "rb") as f1, open(valid2, "rb") as f2, open(
                invalid, "rb"
            ) as f3:
                response = client.post(
                    "/api/v1/upload_report",
                    files=[
                        ("files", ("page1.pdf", f1, "application/pdf")),
                        ("files", ("page2.pdf", f2, "application/pdf")),
                        ("files", ("badfile.txt", f3, "text/plain")),
                    ],
                )

            # Should succeed with 2 files
            assert response.status_code == 200
            data = response.json()
            assert data["upload_stats"]["total_files"] == 3
            assert data["upload_stats"]["successfully_parsed"] == 2
            assert len(data["upload_stats"]["failed_files"]) == 1
            assert any("badfile" in f for f in data["upload_stats"]["failed_files"])

    def test_multi_file_all_files_invalid(self, client, tmp_path):
        """Test error when all files fail validation."""
        # Create 2 invalid files
        invalid1 = tmp_path / "bad1.txt"
        invalid2 = tmp_path / "bad2.exe"

        invalid1.write_bytes(b"not a pdf")
        invalid2.write_bytes(b"executable")

        with patch("src.api.server.LegacyParser.validate_file") as MockValidate:
            # All files fail validation
            MockValidate.return_value = {
                "valid": False,
                "error": "Invalid file format",
            }

            with open(invalid1, "rb") as f1, open(invalid2, "rb") as f2:
                response = client.post(
                    "/api/v1/upload_report",
                    files=[
                        ("files", ("bad1.txt", f1, "text/plain")),
                        ("files", ("bad2.exe", f2, "application/octet-stream")),
                    ],
                )

            assert response.status_code == 400
            data = response.json()
            assert "AllFilesInvalid" in data["detail"]["error"]

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

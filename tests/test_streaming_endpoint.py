import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from src.api.server import app

from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_upload_report_stream_endpoint():
    # Mock dependencies
    with patch("src.api.server.validate_multi_file_upload") as mock_validate, \
         patch("src.api.server.LegacyParser.validate_file") as mock_validate_file, \
         patch("src.api.server.OCRParser") as MockOCRParser, \
         patch("src.api.server.Orchestrator") as MockOrchestrator, \
         patch("src.api.server.LegacyParser.merge_parsed_with_user_input") as mock_merge:
        
        # Setup mocks
        mock_validate.return_value = {"valid": True, "error": None}
        mock_validate_file.return_value = {"valid": True}
        
        mock_parser_instance = MockOCRParser.return_value
        mock_parser_instance.parse_batch = AsyncMock(return_value={"merged_data": {"cholesterol": "high"}, "results": []})
        
        mock_orchestrator_instance = MockOrchestrator.return_value
        
        # Mock execute to simulate progress and return result
        async def mock_execute(health_report, user_profile, progress_callback=None):
            if progress_callback:
                await progress_callback("Agent 1 working...")
                await asyncio.sleep(0.01)
                await progress_callback("Agent 2 working...")
            
            return {
                "session_id": "test-session",
                "status": "approved",
                "plan": "Eat healthy",
                "risk_tags": ["high_cholesterol"],
                "iterations": 1
            }
            
        mock_orchestrator_instance.execute = mock_execute
        
        # Create dummy file
        files = [("files", ("report.pdf", b"dummy content", "application/pdf"))]
        
        # Call endpoint using AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            async with ac.stream("POST", "/api/v1/upload_report_stream", files=files) as response:
                assert response.status_code == 200
                
                events = []
                async for line in response.aiter_lines():
                    if line:
                        events.append(line)
                
                # Verify events
                assert any("event: progress" in e for e in events)
                assert any("Agent 1 working..." in e for e in events)
                assert any("Agent 2 working..." in e for e in events)
                assert any("event: result" in e for e in events)
                
                # Verify result payload
                result_line = next(e for e in events if "session_id" in e)
                assert "Eat healthy" in result_line

if __name__ == "__main__":
    # Manually run the test function if executed directly
    # (Requires async environment)
    pass

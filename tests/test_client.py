"""Tests for NLP Agent client."""

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from nlp_agent.client.client import NLPAgentClient, NLPAgentClientError, RateLimitError
from nlp_agent.models.schemas import HealthResponse, QueryResponse, QueryStatus


@pytest.fixture
def mock_response():
    """Mock HTTP response fixture."""
    response = AsyncMock(spec=httpx.Response)
    response.status_code = 200
    return response


@pytest.mark.asyncio
async def test_health_check(mock_response):
    """Test client health check."""
    mock_response.json.return_value = {
        "status": "healthy",
        "timestamp": "2023-01-01T00:00:00",
        "version": "0.1.0"
    }
    
    with patch('httpx.AsyncClient.request', return_value=mock_response):
        async with NLPAgentClient() as client:
            response = await client.health_check()
            
            assert isinstance(response, HealthResponse)
            assert response.status == "healthy"
            assert response.version == "0.1.0"


@pytest.mark.asyncio
async def test_process_query(mock_response):
    """Test client query processing."""
    mock_response.json.return_value = {
        "id": "test-id",
        "status": "completed",
        "created_at": "2023-01-01T00:00:00",
        "result": {"query": "test query"}
    }
    
    with patch('httpx.AsyncClient.request', return_value=mock_response):
        async with NLPAgentClient() as client:
            response = await client.process_query("test query")
            
            assert isinstance(response, QueryResponse)
            assert response.id == "test-id"
            assert response.status == QueryStatus.COMPLETED


@pytest.mark.asyncio
async def test_list_queries(mock_response):
    """Test client query listing."""
    mock_response.json.return_value = {
        "queries": [],
        "pagination": {
            "page": 1,
            "limit": 20,
            "total": 0,
            "pages": 0,
            "has_next": False,
            "has_prev": False
        }
    }
    
    with patch('httpx.AsyncClient.request', return_value=mock_response):
        async with NLPAgentClient() as client:
            response = await client.list_queries()
            
            assert len(response.queries) == 0
            assert response.pagination.page == 1
            assert response.pagination.total == 0


@pytest.mark.asyncio
async def test_execute_cli(mock_response):
    """Test client CLI execution."""
    mock_response.json.return_value = {
        "stdout": "output",
        "stderr": "",
        "exit_code": 0,
        "duration_ms": 100.0
    }
    
    with patch('httpx.AsyncClient.request', return_value=mock_response):
        async with NLPAgentClient() as client:
            response = await client.execute_cli("clio_service", "list")
            
            assert response.stdout == "output"
            assert response.exit_code == 0
            assert response.duration_ms == 100.0


@pytest.mark.asyncio
async def test_rate_limit_error():
    """Test rate limit error handling."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 429
    
    with patch('httpx.AsyncClient.request', return_value=mock_response):
        async with NLPAgentClient() as client:
            with pytest.raises(RateLimitError):
                await client.health_check()


@pytest.mark.asyncio
async def test_api_error():
    """Test API error handling."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "error": "bad_request",
        "message": "Invalid request"
    }
    
    with patch('httpx.AsyncClient.request', return_value=mock_response):
        async with NLPAgentClient() as client:
            with pytest.raises(NLPAgentClientError, match="API error: Invalid request"):
                await client.health_check()


@pytest.mark.asyncio
async def test_request_error():
    """Test request error handling."""
    with patch('httpx.AsyncClient.request', side_effect=httpx.RequestError("Connection failed")):
        async with NLPAgentClient() as client:
            with pytest.raises(NLPAgentClientError, match="Request failed"):
                await client.health_check()


def test_client_configuration():
    """Test client configuration."""
    client = NLPAgentClient(
        base_url="http://example.com:8080",
        timeout=60.0,
        headers={"Authorization": "Bearer token"}
    )
    
    assert client.base_url == "http://example.com:8080"
    assert client.timeout == 60.0
    assert "Authorization" in client.headers


@pytest.mark.asyncio
async def test_context_manager():
    """Test client as async context manager."""
    async with NLPAgentClient() as client:
        assert client.client is not None
    
    # Client should be closed after context exit
    assert client.client.is_closed
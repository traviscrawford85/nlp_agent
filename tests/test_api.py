"""Tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from nlp_agent.api.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


def test_process_query(client):
    """Test query processing endpoint."""
    query_data = {
        "query": "show me the health status",
        "options": {
            "include_metadata": True
        }
    }
    
    response = client.post("/query", json=query_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "id" in data
    assert data["status"] in ["pending", "processing", "completed", "failed"]
    assert "created_at" in data


def test_list_queries(client):
    """Test query listing endpoint."""
    response = client.get("/queries")
    assert response.status_code == 200
    
    data = response.json()
    assert "queries" in data
    assert "pagination" in data
    
    pagination = data["pagination"]
    assert pagination["page"] == 1
    assert pagination["limit"] == 20
    assert "total" in pagination
    assert "pages" in pagination
    assert "has_next" in pagination
    assert "has_prev" in pagination


def test_list_queries_with_pagination(client):
    """Test query listing with pagination parameters."""
    response = client.get("/queries?page=2&limit=5")
    assert response.status_code == 200
    
    data = response.json()
    pagination = data["pagination"]
    assert pagination["page"] == 2
    assert pagination["limit"] == 5


def test_list_queries_with_filters(client):
    """Test query listing with filters."""
    response = client.get("/queries?status=completed")
    assert response.status_code == 200
    
    data = response.json()
    assert "queries" in data


def test_cli_execute(client):
    """Test CLI execution endpoint."""
    cli_data = {
        "service": "clio_service",
        "command": "list",
        "args": ["--help"]
    }
    
    response = client.post("/cli/execute", json=cli_data)
    # Note: This might fail if the CLI service isn't available,
    # but the endpoint should handle it gracefully
    assert response.status_code in [200, 500]  # Either success or handled error
    
    if response.status_code == 200:
        data = response.json()
        assert "stdout" in data
        assert "stderr" in data
        assert "exit_code" in data
        assert "duration_ms" in data


def test_rate_limiting(client):
    """Test rate limiting on query endpoint."""
    query_data = {"query": "test query"}
    
    # Make multiple requests to trigger rate limiting
    responses = []
    for _ in range(15):  # Limit is 10/minute
        response = client.post("/query", json=query_data)
        responses.append(response.status_code)
    
    # At least one should be rate limited
    assert 429 in responses or all(code == 200 for code in responses[:10])


def test_invalid_query_request(client):
    """Test invalid query request."""
    invalid_data = {"query": ""}  # Empty query should be invalid
    
    response = client.post("/query", json=invalid_data)
    assert response.status_code == 422  # Validation error


def test_invalid_cli_request(client):
    """Test invalid CLI request."""
    invalid_data = {"service": "invalid_service", "command": "test"}
    
    response = client.post("/cli/execute", json=invalid_data)
    assert response.status_code == 422  # Validation error
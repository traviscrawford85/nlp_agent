"""Tests for Pydantic models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from nlp_agent.models.schemas import (
    QueryRequest,
    QueryResponse,
    QueryStatus,
    CLIRequest,
    CLIService,
    HealthResponse,
    PaginationInfo,
)


def test_query_request_validation():
    """Test QueryRequest validation."""
    # Valid request
    request = QueryRequest(query="test query")
    assert request.query == "test query"
    assert request.context is None
    assert request.options is None
    
    # With options
    request_with_options = QueryRequest(
        query="test query",
        options={"timeout": 60, "include_metadata": True}
    )
    assert request_with_options.options.timeout == 60
    assert request_with_options.options.include_metadata is True
    
    # Invalid - empty query
    with pytest.raises(ValidationError):
        QueryRequest(query="")
    
    # Invalid - query too long
    with pytest.raises(ValidationError):
        QueryRequest(query="x" * 1001)


def test_query_response():
    """Test QueryResponse model."""
    response = QueryResponse(
        id="test-id",
        status=QueryStatus.COMPLETED,
        created_at=datetime.now(),
    )
    
    assert response.id == "test-id"
    assert response.status == QueryStatus.COMPLETED
    assert response.result is None
    assert response.api_calls is None
    assert response.cli_calls is None


def test_cli_request_validation():
    """Test CLIRequest validation."""
    # Valid request
    request = CLIRequest(
        service=CLIService.CLIO_SERVICE,
        command="list"
    )
    assert request.service == CLIService.CLIO_SERVICE
    assert request.command == "list"
    assert request.args is None
    
    # With args and input data
    request_with_data = CLIRequest(
        service=CLIService.CUSTOM_FIELDS_MANAGER,
        command="create",
        args=["--name", "test"],
        input_data={"field_type": "text"}
    )
    assert request_with_data.args == ["--name", "test"]
    assert request_with_data.input_data == {"field_type": "text"}


def test_health_response():
    """Test HealthResponse model."""
    response = HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="0.1.0"
    )
    
    assert response.status == "healthy"
    assert response.version == "0.1.0"


def test_pagination_info():
    """Test PaginationInfo model."""
    pagination = PaginationInfo(
        page=2,
        limit=20,
        total=100,
        pages=5,
        has_next=True,
        has_prev=True
    )
    
    assert pagination.page == 2
    assert pagination.total == 100
    assert pagination.has_next is True
    assert pagination.has_prev is True
    
    # Invalid - negative values
    with pytest.raises(ValidationError):
        PaginationInfo(
            page=0,  # Should be >= 1
            limit=20,
            total=100,
            pages=5,
            has_next=True,
            has_prev=False
        )


def test_query_status_enum():
    """Test QueryStatus enum."""
    assert QueryStatus.PENDING == "pending"
    assert QueryStatus.PROCESSING == "processing"
    assert QueryStatus.COMPLETED == "completed"
    assert QueryStatus.FAILED == "failed"


def test_cli_service_enum():
    """Test CLIService enum."""
    assert CLIService.CLIO_SERVICE == "clio_service"
    assert CLIService.CUSTOM_FIELDS_MANAGER == "custom-fields-manager"
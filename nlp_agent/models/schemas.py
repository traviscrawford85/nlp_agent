"""Pydantic models generated from OpenAPI specification."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryStatus(str, Enum):
    """Query processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HTTPMethod(str, Enum):
    """HTTP methods for API calls."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class CLIService(str, Enum):
    """Available CLI services."""
    CLIO_SERVICE = "clio_service"
    CUSTOM_FIELDS_MANAGER = "custom-fields-manager"


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    timestamp: datetime
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})


class QueryOptions(BaseModel):
    """Options for query processing."""
    timeout: int = Field(default=30, ge=1, le=300, description="Query timeout in seconds")
    include_metadata: bool = Field(default=False, description="Include processing metadata in response")


class QueryRequest(BaseModel):
    """Request for natural language query processing."""
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language query to process")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context for the query")
    options: Optional[QueryOptions] = None


class APICall(BaseModel):
    """API call information."""
    endpoint: str
    method: HTTPMethod
    payload: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None


class CLICall(BaseModel):
    """CLI call information."""
    command: str
    args: List[str]
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: int
    duration_ms: Optional[float] = None


class QueryMetadata(BaseModel):
    """Query processing metadata."""
    processing_time_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)


class QueryResponse(BaseModel):
    """Response for processed query."""
    id: str = Field(..., description="Unique query identifier")
    status: QueryStatus
    result: Optional[Dict[str, Any]] = Field(None, description="Query processing result")
    api_calls: Optional[List[APICall]] = None
    cli_calls: Optional[List[CLICall]] = None
    metadata: Optional[QueryMetadata] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class PaginationInfo(BaseModel):
    """Pagination information."""
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1)
    total: int = Field(..., ge=0)
    pages: int = Field(..., ge=0)
    has_next: bool
    has_prev: bool


class QueryListResponse(BaseModel):
    """Response for query list with pagination."""
    queries: List[QueryResponse]
    pagination: PaginationInfo


class CLIRequest(BaseModel):
    """Request for CLI command execution."""
    service: CLIService = Field(..., description="CLI service to execute")
    command: str = Field(..., description="Command to execute")
    args: Optional[List[str]] = Field(None, description="Command arguments")
    input_data: Optional[Dict[str, Any]] = Field(None, description="JSON payload to pass to the command")


class CLIResponse(BaseModel):
    """Response for CLI command execution."""
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    parsed_output: Optional[Dict[str, Any]] = Field(None, description="Parsed JSON output if applicable")


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
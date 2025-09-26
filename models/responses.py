"""
Pydantic models for response serialization.

This module defines the response models used by the FastAPI application
for structuring responses from the NLP endpoint.
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from pydantic import BaseModel, Field


class NLPResponse(BaseModel):
    """Response model for the /nlp endpoint."""

    success: bool = Field(..., description="Whether the operation was successful")

    message: str = Field(
        ...,
        description="Human-readable explanation of what was done",
        example="Created a new contact 'John Doe' with email john@example.com"
    )

    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(
        None,
        description="Structured data result from the operation"
    )

    raw_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Raw API responses (if requested)"
    )

    operation_type: str = Field(
        ...,
        description="Type of operation performed",
        example="create_contact"
    )

    entities_affected: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of entities that were affected by the operation",
        example=[{"type": "contact", "id": "12345", "name": "John Doe"}]
    )

    execution_time: float = Field(
        ...,
        description="Time taken to process the request in seconds"
    )

    warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings generated during processing"
    )


class ErrorResponse(BaseModel):
    """Response model for error cases."""

    success: bool = Field(False, description="Always false for error responses")

    error: str = Field(..., description="Error type or code")

    message: str = Field(..., description="Human-readable error message")

    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field("1.0.0", description="API version")
    services: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of dependent services"
    )


class ContactResponse(BaseModel):
    """Response model for contact operations."""

    id: str = Field(..., description="Contact ID")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    company: Optional[str] = Field(None, description="Company name")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class MatterResponse(BaseModel):
    """Response model for matter operations."""

    id: str = Field(..., description="Matter ID")
    description: str = Field(..., description="Matter description")
    client: Optional[Dict[str, Any]] = Field(None, description="Client information")
    status: str = Field(..., description="Matter status")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class ActivityResponse(BaseModel):
    """Response model for activity operations."""

    id: str = Field(..., description="Activity ID")
    description: str = Field(..., description="Activity description")
    matter: Optional[Dict[str, Any]] = Field(None, description="Matter information")
    user: Optional[Dict[str, Any]] = Field(None, description="User information")
    quantity: float = Field(..., description="Time quantity in seconds")
    date: Optional[str] = Field(None, description="Activity date")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class CustomFieldResponse(BaseModel):
    """Response model for custom field operations."""

    id: str = Field(..., description="Custom field ID")
    name: str = Field(..., description="Field name")
    entity_type: str = Field(..., description="Entity type")
    field_type: str = Field(..., description="Field type")
    required: bool = Field(..., description="Whether field is required")
    options: Optional[List[str]] = Field(None, description="Field options")


class SearchResponse(BaseModel):
    """Response model for search operations."""

    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of results found")
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    took_ms: int = Field(..., description="Search time in milliseconds")
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters that were applied"
    )


class BulkOperationResponse(BaseModel):
    """Response model for bulk operations."""

    operation: str = Field(..., description="Type of bulk operation")
    total_items: int = Field(..., description="Total items processed")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    errors: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of errors that occurred"
    )
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Results for each item processed"
    )


class ReportResponse(BaseModel):
    """Response model for report generation."""

    report_type: str = Field(..., description="Type of report generated")
    format: str = Field(..., description="Report format")
    data: Union[Dict[str, Any], List[Dict[str, Any]], str] = Field(
        ...,
        description="Report data"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters used to generate the report"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the report was generated"
    )


class ToolExecutionResult(BaseModel):
    """Result of a tool execution within the agent."""

    tool_name: str = Field(..., description="Name of the tool that was executed")
    success: bool = Field(..., description="Whether the tool execution succeeded")
    output: Any = Field(..., description="Tool output")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time: float = Field(..., description="Execution time in seconds")


class AgentThought(BaseModel):
    """Represents a thought or reasoning step from the agent."""

    step: int = Field(..., description="Step number in the reasoning process")
    thought: str = Field(..., description="Agent's thought or reasoning")
    action: Optional[str] = Field(None, description="Action the agent decided to take")
    observation: Optional[str] = Field(None, description="Observation from action result")


class DetailedNLPResponse(NLPResponse):
    """Extended NLP response with agent reasoning details."""

    agent_thoughts: List[AgentThought] = Field(
        default_factory=list,
        description="Step-by-step reasoning from the agent"
    )

    tools_used: List[ToolExecutionResult] = Field(
        default_factory=list,
        description="Details of all tools that were executed"
    )

    confidence_score: Optional[float] = Field(
        None,
        description="Confidence score for the result (0-1)",
        ge=0,
        le=1
    )
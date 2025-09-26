"""
Pydantic models for request validation.

This module defines the request models used by the FastAPI application
for validating incoming requests to the NLP endpoint.
"""

from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, validator


class NLPRequest(BaseModel):
    """Request model for the /nlp endpoint."""

    query: str = Field(
        ...,
        description="Natural language query to process",
        min_length=1,
        max_length=2000,
        example="Create a new contact named John Doe with email john@example.com"
    )

    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context for the query (user preferences, etc.)",
        example={"user_id": "123", "default_matter": "456"}
    )

    include_raw_data: bool = Field(
        True,
        description="Whether to include raw API responses in the result"
    )

    max_results: Optional[int] = Field(
        None,
        description="Maximum number of results to return for list operations",
        ge=1,
        le=1000
    )

    timeout: Optional[int] = Field(
        60,
        description="Maximum time in seconds to process the request",
        ge=5,
        le=300
    )

    @validator('query')
    def validate_query(cls, v):
        """Validate that query is not just whitespace."""
        if not v or not v.strip():
            raise ValueError('Query cannot be empty or just whitespace')
        return v.strip()


class ContactCreateRequest(BaseModel):
    """Request model for creating contacts via API."""

    first_name: str = Field(..., description="First name of the contact")
    last_name: str = Field(..., description="Last name of the contact")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    company: Optional[str] = Field(None, description="Company name")
    address: Optional[Dict[str, str]] = Field(None, description="Address information")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom field values")


class MatterCreateRequest(BaseModel):
    """Request model for creating matters via API."""

    description: str = Field(..., description="Matter description")
    client_id: str = Field(..., description="ID of the client for this matter")
    status: Optional[str] = Field("Open", description="Matter status")
    practice_area: Optional[str] = Field(None, description="Practice area")
    billable: Optional[bool] = Field(True, description="Whether the matter is billable")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom field values")


class ActivityCreateRequest(BaseModel):
    """Request model for creating activities/time entries."""

    matter_id: str = Field(..., description="ID of the matter")
    description: str = Field(..., description="Description of the activity")
    quantity: float = Field(..., description="Time quantity in seconds", ge=0)
    date: Optional[str] = Field(None, description="Date of the activity (YYYY-MM-DD)")
    rate: Optional[float] = Field(None, description="Hourly rate", ge=0)
    user_id: Optional[str] = Field(None, description="ID of the user performing the activity")


class CustomFieldRequest(BaseModel):
    """Request model for custom field operations."""

    name: str = Field(..., description="Name of the custom field")
    entity_type: str = Field(..., description="Entity type (Contact, Matter, etc.)")
    field_type: str = Field(..., description="Field type (text, number, date, etc.)")
    options: Optional[List[str]] = Field(None, description="Options for choice fields")
    required: bool = Field(False, description="Whether the field is required")
    description: Optional[str] = Field(None, description="Field description")


class SearchRequest(BaseModel):
    """Request model for search operations."""

    query: str = Field(..., description="Search query")
    entity_type: str = Field(..., description="Type of entity to search (contacts, matters, etc.)")
    limit: Optional[int] = Field(50, description="Maximum number of results", ge=1, le=200)
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional search filters")


class BulkOperationRequest(BaseModel):
    """Request model for bulk operations."""

    operation: str = Field(..., description="Type of bulk operation")
    entity_type: str = Field(..., description="Type of entity to operate on")
    data: List[Dict[str, Any]] = Field(..., description="List of data for bulk operation")
    batch_size: Optional[int] = Field(10, description="Batch size for processing", ge=1, le=50)


class AuthRequest(BaseModel):
    """Request model for authentication operations."""

    username: Optional[str] = Field(None, description="Username for authentication")
    password: Optional[str] = Field(None, description="Password for authentication")
    token: Optional[str] = Field(None, description="Existing authentication token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")


class ReportRequest(BaseModel):
    """Request model for generating reports."""

    report_type: str = Field(..., description="Type of report to generate")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Report parameters")
    format: str = Field("json", description="Output format (json, csv, pdf)")
    date_from: Optional[str] = Field(None, description="Start date for report")
    date_to: Optional[str] = Field(None, description="End date for report")
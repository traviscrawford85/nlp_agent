"""
Clio API wrapper with rate limiting and pagination.

This module provides a high-level interface to the Clio API with automatic
rate limiting, pagination handling, and authentication management.
"""

import os
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime

from loguru import logger
from pydantic import BaseModel

from services.rate_limiter import ClioAPIClient


class ClioAPIWrapper:
    """High-level wrapper for Clio API operations."""

    def __init__(self, auth_token: Optional[str] = None, base_url: str = "https://app.clio.com/api/v4"):
        self.client = ClioAPIClient(base_url=base_url, auth_token=auth_token)
        if auth_token:
            self.client.set_auth_token(auth_token)

    def set_auth_token(self, token: str):
        """Set the authentication token."""
        self.client.set_auth_token(token)

    async def close(self):
        """Close the API client."""
        await self.client.close()

    # Contact operations
    async def get_contacts(
        self,
        limit: Optional[int] = None,
        search: Optional[str] = None,
        email: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get contacts from Clio.

        Args:
            limit: Maximum number of contacts to return
            search: Search query for contact names
            email: Filter by email address

        Returns:
            List of contact dictionaries
        """
        params = {}
        if search:
            params["query"] = search
        if email:
            params["email"] = email

        if limit:
            # Get limited results
            params["per_page"] = min(limit, 200)
            response = await self.client.request("GET", "contacts.json", params=params)
            data = response.json()
            contacts = data.get("data", [])
            return contacts[:limit] if len(contacts) > limit else contacts
        else:
            # Get all results with pagination
            return await self.client.get_all("contacts.json", params)

    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contact in Clio."""
        response = await self.client.request("POST", "contacts.json", json_data={"data": contact_data})
        return response.json().get("data", {})

    async def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing contact in Clio."""
        response = await self.client.request("PUT", f"contacts/{contact_id}.json", json_data={"data": contact_data})
        return response.json().get("data", {})

    async def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """Get a single contact by ID."""
        response = await self.client.request("GET", f"contacts/{contact_id}.json")
        return response.json().get("data", {})

    async def delete_contact(self, contact_id: str) -> bool:
        """Delete a contact from Clio."""
        response = await self.client.request("DELETE", f"contacts/{contact_id}.json")
        return response.status_code == 204

    # Matter operations
    async def get_matters(
        self,
        limit: Optional[int] = None,
        client_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get matters from Clio.

        Args:
            limit: Maximum number of matters to return
            client_id: Filter by client ID
            status: Filter by matter status

        Returns:
            List of matter dictionaries
        """
        params = {}
        if client_id:
            params["client_id"] = client_id
        if status:
            params["status"] = status

        if limit:
            params["per_page"] = min(limit, 200)
            response = await self.client.request("GET", "matters.json", params=params)
            data = response.json()
            matters = data.get("data", [])
            return matters[:limit] if len(matters) > limit else matters
        else:
            return await self.client.get_all("matters.json", params)

    async def create_matter(self, matter_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new matter in Clio."""
        response = await self.client.request("POST", "matters.json", json_data={"data": matter_data})
        return response.json().get("data", {})

    async def update_matter(self, matter_id: str, matter_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing matter in Clio."""
        response = await self.client.request("PUT", f"matters/{matter_id}.json", json_data={"data": matter_data})
        return response.json().get("data", {})

    async def get_matter(self, matter_id: str) -> Dict[str, Any]:
        """Get a single matter by ID."""
        response = await self.client.request("GET", f"matters/{matter_id}.json")
        return response.json().get("data", {})

    # Activity/Time tracking operations
    async def get_activities(
        self,
        limit: Optional[int] = None,
        matter_id: Optional[str] = None,
        user_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get activities/time entries from Clio.

        Args:
            limit: Maximum number of activities to return
            matter_id: Filter by matter ID
            user_id: Filter by user ID
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            List of activity dictionaries
        """
        params = {}
        if matter_id:
            params["matter_id"] = matter_id
        if user_id:
            params["user_id"] = user_id
        if date_from:
            params["created_at_from"] = date_from
        if date_to:
            params["created_at_to"] = date_to

        if limit:
            params["per_page"] = min(limit, 200)
            response = await self.client.request("GET", "activities.json", params=params)
            data = response.json()
            activities = data.get("data", [])
            return activities[:limit] if len(activities) > limit else activities
        else:
            return await self.client.get_all("activities.json", params)

    async def create_activity(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new activity/time entry in Clio."""
        response = await self.client.request("POST", "activities.json", json_data={"data": activity_data})
        return response.json().get("data", {})

    async def update_activity(self, activity_id: str, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing activity in Clio."""
        response = await self.client.request("PUT", f"activities/{activity_id}.json", json_data={"data": activity_data})
        return response.json().get("data", {})

    # Document operations
    async def get_documents(
        self,
        limit: Optional[int] = None,
        matter_id: Optional[str] = None,
        document_category_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get documents from Clio.

        Args:
            limit: Maximum number of documents to return
            matter_id: Filter by matter ID
            document_category_id: Filter by document category

        Returns:
            List of document dictionaries
        """
        params = {}
        if matter_id:
            params["matter_id"] = matter_id
        if document_category_id:
            params["document_category_id"] = document_category_id

        if limit:
            params["per_page"] = min(limit, 200)
            response = await self.client.request("GET", "documents.json", params=params)
            data = response.json()
            documents = data.get("data", [])
            return documents[:limit] if len(documents) > limit else documents
        else:
            return await self.client.get_all("documents.json", params)

    async def upload_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a document to Clio."""
        response = await self.client.request("POST", "documents.json", json_data={"data": document_data})
        return response.json().get("data", {})

    # Custom field operations
    async def get_custom_fields(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get custom field definitions from Clio.

        Args:
            entity_type: Filter by entity type (Contact, Matter, etc.)

        Returns:
            List of custom field dictionaries
        """
        params = {}
        if entity_type:
            params["parent_type"] = entity_type

        return await self.client.get_all("custom_fields.json", params)

    async def create_custom_field(self, field_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new custom field in Clio."""
        response = await self.client.request("POST", "custom_fields.json", json_data={"data": field_data})
        return response.json().get("data", {})

    async def update_custom_field(self, field_id: str, field_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing custom field in Clio."""
        response = await self.client.request("PUT", f"custom_fields/{field_id}.json", json_data={"data": field_data})
        return response.json().get("data", {})

    async def get_custom_field_values(
        self,
        entity_type: str,
        entity_id: str,
        field_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get custom field values for an entity.

        Args:
            entity_type: Type of entity (contact, matter, etc.)
            entity_id: ID of the entity
            field_id: Specific field ID (optional)

        Returns:
            List of custom field value dictionaries
        """
        endpoint = f"{entity_type}s/{entity_id}/custom_field_values.json"
        params = {}
        if field_id:
            params["custom_field_id"] = field_id

        return await self.client.get_all(endpoint, params)

    async def set_custom_field_value(
        self,
        entity_type: str,
        entity_id: str,
        field_id: str,
        value: Any
    ) -> Dict[str, Any]:
        """Set a custom field value for an entity."""
        endpoint = f"{entity_type}s/{entity_id}/custom_field_values.json"
        data = {
            "custom_field": {"id": field_id},
            "value": value
        }
        response = await self.client.request("POST", endpoint, json_data={"data": data})
        return response.json().get("data", {})

    # Generic API operations
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request to any Clio API endpoint."""
        response = await self.client.request("GET", endpoint, params=params)
        return response.json()

    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to any Clio API endpoint."""
        response = await self.client.request("POST", endpoint, json_data=data)
        return response.json()

    async def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a PUT request to any Clio API endpoint."""
        response = await self.client.request("PUT", endpoint, json_data=data)
        return response.json()

    async def delete(self, endpoint: str) -> bool:
        """Make a DELETE request to any Clio API endpoint."""
        response = await self.client.request("DELETE", endpoint)
        return response.status_code in [200, 204]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
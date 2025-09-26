"""
Clio Private UI API Client
Handles Clio's internal UI endpoints for advanced configuration management.
"""

import json
import os
from typing import Optional, Dict, Any, List
from loguru import logger
import requests
from urllib.parse import urlencode

from services.clio_session import ClioSessionManager


class ClioPrivateAPIClient:
    """Client for Clio's private UI API endpoints."""

    def __init__(self, session_manager: ClioSessionManager):
        self.session_manager = session_manager
        self.base_url = "https://app.clio.com"

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        form_encoded: bool = False
    ) -> Dict[str, Any]:
        """
        Make authenticated request to private API endpoint.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            form_encoded: Whether to use form encoding

        Returns:
            Response dictionary with success/error status
        """
        session_cookie = self.session_manager.get_active_session_cookie()
        if not session_cookie:
            return {
                "success": False,
                "error": "No active session cookie available. Please authenticate first."
            }

        headers = {
            "Cookie": f"_clio_session={session_cookie}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "application/json"
        }

        if form_encoded and data:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            request_data = urlencode(data, doseq=True)
        else:
            headers["Content-Type"] = "application/json"
            request_data = json.dumps(data) if data else None

        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=request_data,
                params=params,
                timeout=30
            )

            logger.debug(f"{method} {endpoint} -> {response.status_code}")

            if response.status_code in [200, 201]:
                try:
                    response_data = response.json()
                    return {
                        "success": True,
                        "data": response_data,
                        "status_code": response.status_code
                    }
                except json.JSONDecodeError:
                    # Some endpoints return HTML or plain text
                    return {
                        "success": True,
                        "data": response.text,
                        "content_type": response.headers.get("content-type", ""),
                        "status_code": response.status_code
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"Request failed: {e}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }

    # Custom Field Set Operations (enhanced from existing implementation)
    def update_custom_field_set_advanced(
        self,
        field_set_id: str,
        name: str,
        parent_type: str,
        custom_field_ids: List[str],
        displayed: bool = True
    ) -> Dict[str, Any]:
        """
        Update custom field set with advanced options including display state.

        Args:
            field_set_id: ID of the custom field set
            name: Name of the field set
            parent_type: Parent type (e.g., "Matter", "Contact")
            custom_field_ids: List of custom field IDs
            displayed: Whether the field set should be displayed

        Returns:
            Response dictionary
        """
        logger.info(f"Updating custom field set {field_set_id} (advanced)")

        # Prepare form data according to private API spec
        form_data = {
            "_method": "patch",
            "custom_field_set[name]": name,
            "custom_field_set[parent_type]": parent_type,
            "custom_field_set[displayed]": displayed
        }

        # Add custom field IDs as array parameters
        for field_id in custom_field_ids:
            form_data[f"custom_field_set[custom_field_ids][]"] = field_id

        return self._make_request(
            method="POST",
            endpoint=f"/settings/custom_field_sets/{field_set_id}",
            data=form_data,
            form_encoded=True
        )

    # Custom Fields Operations
    def get_custom_fields(
        self,
        parent_type: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get custom fields filtered by parent type.

        Args:
            parent_type: Filter by parent type (e.g., "matter", "contact")
            prefix: Prefix for field names

        Returns:
            Response dictionary with custom fields data
        """
        logger.info(f"Retrieving custom fields for {parent_type or 'all types'}")

        params = {}
        if parent_type:
            params["parent_type"] = parent_type
        if prefix:
            params["prefix"] = prefix

        return self._make_request(
            method="GET",
            endpoint="/settings/custom_fields",
            params=params
        )

    # Matter Numbering Operations
    def get_matter_numbering_settings(self) -> Dict[str, Any]:
        """
        Get matter numbering configuration.

        Returns:
            Response dictionary with numbering settings
        """
        logger.info("Retrieving matter numbering settings")

        return self._make_request(
            method="GET",
            endpoint="/settings/matter_numbering"
        )

    def update_matter_numbering_settings(
        self,
        prefix: Optional[str] = None,
        sequence: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update matter numbering settings.

        Args:
            prefix: Matter number prefix (e.g., "MAT-")
            sequence: Starting sequence number
            format_type: Numbering format (e.g., "prefix-number")

        Returns:
            Response dictionary
        """
        logger.info("Updating matter numbering settings")

        form_data = {}
        if prefix is not None:
            form_data["matter_numbering[prefix]"] = prefix
        if sequence is not None:
            form_data["matter_numbering[sequence]"] = sequence
        if format_type is not None:
            form_data["matter_numbering[format]"] = format_type

        return self._make_request(
            method="POST",
            endpoint="/settings/matter_numbering",
            data=form_data,
            form_encoded=True
        )

    # Utility Methods
    def get_all_settings_data(self) -> Dict[str, Any]:
        """
        Retrieve comprehensive settings data from multiple endpoints.

        Returns:
            Combined settings data from all available endpoints
        """
        logger.info("Retrieving comprehensive settings data")

        results = {
            "custom_fields": {},
            "matter_numbering": {},
            "success": True,
            "errors": []
        }

        # Get custom fields for different parent types
        for parent_type in ["matter", "contact", "activity"]:
            fields_result = self.get_custom_fields(parent_type=parent_type)
            if fields_result.get("success"):
                results["custom_fields"][parent_type] = fields_result.get("data", [])
            else:
                results["errors"].append(f"Failed to get {parent_type} custom fields: {fields_result.get('error')}")

        # Get matter numbering settings
        numbering_result = self.get_matter_numbering_settings()
        if numbering_result.get("success"):
            results["matter_numbering"] = numbering_result.get("data", {})
        else:
            results["errors"].append(f"Failed to get matter numbering: {numbering_result.get('error')}")

        if results["errors"]:
            results["success"] = False

        return results


if __name__ == "__main__":
    # Example usage
    from services.clio_session import ClioSessionManager

    session_manager = ClioSessionManager()
    client = ClioPrivateAPIClient(session_manager)

    # Test getting custom fields
    print("Testing custom fields retrieval...")
    result = client.get_custom_fields(parent_type="matter")
    print(json.dumps(result, indent=2))

    # Test getting matter numbering settings
    print("\nTesting matter numbering settings...")
    result = client.get_matter_numbering_settings()
    print(json.dumps(result, indent=2))

    # Test comprehensive settings
    print("\nTesting comprehensive settings...")
    result = client.get_all_settings_data()
    print(json.dumps(result, indent=2))
"""
Clio Custom Field Set Management Tools
Handles custom field set operations using Clio web UI endpoints.
"""

import json
from typing import Dict, Any, List
from loguru import logger
from langchain.tools import Tool

from services.clio_session import ClioSessionManager, ClioCustomFieldSetManager


def update_custom_field_set_func(
    field_set_id: str,
    name: str,
    parent_type: str,
    custom_field_ids: str  # JSON string of list
) -> str:
    """
    Update a Clio custom field set with new field ordering.

    Args:
        field_set_id: ID of the custom field set to update
        name: Name of the custom field set
        parent_type: Parent type (e.g., 'Matter', 'Contact', 'Activity')
        custom_field_ids: JSON string containing list of custom field IDs

    Returns:
        JSON string with operation result
    """
    try:
        # Parse the custom field IDs
        field_ids = json.loads(custom_field_ids) if isinstance(custom_field_ids, str) else custom_field_ids

        logger.info(f"Updating custom field set {field_set_id}")

        session_manager = ClioSessionManager()
        field_manager = ClioCustomFieldSetManager(session_manager)

        result = field_manager.update_custom_field_set(
            field_set_id=field_set_id,
            name=name,
            parent_type=parent_type,
            custom_field_ids=field_ids
        )

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error in update_custom_field_set tool: {e}")
        return json.dumps({
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }, indent=2)


def get_custom_field_sets_func() -> str:
    """
    Get list of Clio custom field sets via web UI endpoints.

    Returns:
        JSON string with custom field sets data
    """
    try:
        logger.info("Retrieving custom field sets")

        session_manager = ClioSessionManager()
        field_manager = ClioCustomFieldSetManager(session_manager)

        result = field_manager.get_custom_field_sets()

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error in get_custom_field_sets tool: {e}")
        return json.dumps({
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }, indent=2)


def authenticate_clio_session_func(email: str, password: str) -> str:
    """
    Authenticate with Clio using automated browser login to obtain session cookie.

    Args:
        email: Clio login email
        password: Clio login password

    Returns:
        JSON string with authentication result
    """
    try:
        logger.info(f"Authenticating Clio session for {email}")

        session_manager = ClioSessionManager()
        cookie = session_manager.fetch_session_cookie(email, password)

        if cookie:
            # Save to environment for future use
            from services.clio_session import save_session_cookie_to_env
            save_success = save_session_cookie_to_env(cookie)

            return json.dumps({
                "success": True,
                "message": "Successfully authenticated with Clio",
                "cookie_saved": save_success,
                "cookie_length": len(cookie)
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": "Failed to authenticate with Clio. Please check credentials."
            }, indent=2)

    except Exception as e:
        logger.error(f"Error in authenticate_clio_session tool: {e}")
        return json.dumps({
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }, indent=2)


def get_custom_field_set_tools() -> List[Tool]:
    """Get all custom field set management tools."""

    tools = [
        Tool(
            name="update_custom_field_set",
            description=(
                "Update a Clio custom field set with new field ordering. "
                "This tool uses the Clio web UI endpoints (not public API) to modify custom field sets. "
                "Requires active session cookie authentication. "
                "Use this when users want to reorder, add, or remove fields from a custom field set. "
                "Parameters: field_set_id, name, parent_type, custom_field_ids (JSON string)"
            ),
            func=update_custom_field_set_func
        ),
        Tool(
            name="get_custom_field_sets",
            description=(
                "Get list of Clio custom field sets via web UI endpoints. "
                "This tool accesses internal Clio endpoints to retrieve field set information. "
                "Requires active session cookie authentication. "
                "No parameters required."
            ),
            func=get_custom_field_sets_func
        ),
        Tool(
            name="authenticate_clio_session",
            description=(
                "Authenticate with Clio using automated browser login to obtain session cookie. "
                "This tool uses Playwright to automate login and extract the session cookie needed "
                "for custom field set operations. Use when session authentication is required. "
                "Parameters: email, password"
            ),
            func=authenticate_clio_session_func
        )
    ]

    return tools


# Example usage for testing
if __name__ == "__main__":
    # Test the tools
    tools = get_custom_field_set_tools()

    print("Available Custom Field Set Tools:")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")

    # Example: Test session authentication
    # auth_tool = next(t for t in tools if t.name == "authenticate_clio_session")
    # result = auth_tool.func("your_email@example.com", "your_password")
    # print("Auth result:", result)
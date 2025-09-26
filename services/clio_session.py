"""
Clio Session Cookie Management
Handles automated login and session cookie extraction for Clio web UI endpoints.
"""

import json
import os
from typing import Optional
from loguru import logger
from playwright.sync_api import sync_playwright
import requests
from urllib.parse import urlencode


class ClioSessionManager:
    """Manages Clio web session cookies for internal API access."""

    def __init__(self):
        self.base_url = "https://app.clio.com"
        self.session_cookie: Optional[str] = None

    def fetch_session_cookie(self, email: str, password: str) -> Optional[str]:
        """
        Fetch Clio session cookie using automated browser login.

        Args:
            email: Clio login email
            password: Clio login password

        Returns:
            Session cookie value or None if failed
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                logger.info("Navigating to Clio login page...")
                page.goto(f"{self.base_url}/session/new")

                # Wait for page to load
                page.wait_for_selector("input[name='email']", timeout=10000)

                logger.info("Entering login credentials...")
                page.fill("input[name='email']", email)
                page.fill("input[name='password']", password)

                # Submit login form
                page.click("button[type='submit']")

                # Wait for login success (dashboard appears)
                logger.info("Waiting for login success...")
                page.wait_for_url(f"{self.base_url}/*", timeout=15000)

                # Extract session cookie
                cookies = context.cookies()
                session_cookie = None

                for cookie in cookies:
                    if cookie["name"] == "_clio_session":
                        session_cookie = cookie["value"]
                        break

                browser.close()

                if session_cookie:
                    logger.info("Successfully extracted Clio session cookie")
                    self.session_cookie = session_cookie
                    return session_cookie
                else:
                    logger.error("Failed to find _clio_session cookie")
                    return None

        except Exception as e:
            logger.error(f"Failed to fetch Clio session cookie: {e}")
            return None

    def get_session_cookie_from_env(self) -> Optional[str]:
        """Get session cookie from environment variable."""
        cookie = os.getenv("CLIO_SESSION_COOKIE")
        if cookie:
            self.session_cookie = cookie
            logger.info("Using Clio session cookie from environment")
        return cookie

    def get_active_session_cookie(self) -> Optional[str]:
        """Get active session cookie, preferring environment variable."""
        # Try environment first
        env_cookie = self.get_session_cookie_from_env()
        if env_cookie:
            return env_cookie

        # Return cached cookie if available
        if self.session_cookie:
            return self.session_cookie

        logger.warning("No active Clio session cookie available")
        return None


class ClioCustomFieldSetManager:
    """Manages Clio custom field sets via web UI endpoints."""

    def __init__(self, session_manager: ClioSessionManager):
        self.session_manager = session_manager
        self.base_url = "https://app.clio.com"

    def update_custom_field_set(
        self,
        field_set_id: str,
        name: str,
        parent_type: str,
        custom_field_ids: list[str]
    ) -> dict:
        """
        Update a custom field set with new field ordering.

        Args:
            field_set_id: ID of the custom field set to update
            name: Name of the field set
            parent_type: Parent type (e.g., "Matter", "Contact")
            custom_field_ids: Ordered list of custom field IDs

        Returns:
            Response dictionary with success/error status
        """
        session_cookie = self.session_manager.get_active_session_cookie()
        if not session_cookie:
            return {
                "success": False,
                "error": "No active session cookie available. Please authenticate first."
            }

        # Prepare form data
        form_data = {
            "_method": "patch",
            "custom_field_set[name]": name,
            "custom_field_set[parent_type]": parent_type
        }

        # Add custom field IDs as array parameters
        for field_id in custom_field_ids:
            form_data[f"custom_field_set[custom_field_ids][]"] = field_id

        # Prepare headers
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": f"_clio_session={session_cookie}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }

        # Build URL
        url = f"{self.base_url}/settings/custom_field_sets/{field_set_id}"

        try:
            logger.info(f"Updating custom field set {field_set_id} with {len(custom_field_ids)} fields")

            # Make the request
            response = requests.post(
                url,
                headers=headers,
                data=urlencode(form_data, doseq=True),
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Successfully updated custom field set {field_set_id}")
                return {
                    "success": True,
                    "message": f"Custom field set '{name}' updated successfully",
                    "field_count": len(custom_field_ids)
                }
            else:
                logger.error(f"Failed to update custom field set: {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"Error updating custom field set: {e}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }

    def get_custom_field_sets(self) -> dict:
        """
        Get list of custom field sets (if endpoint is accessible).

        Returns:
            Response dictionary with field sets data
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

        url = f"{self.base_url}/settings/custom_field_sets"

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.text,
                    "content_type": response.headers.get("content-type", "")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "status_code": response.status_code
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }


def save_session_cookie_to_env(cookie_value: str, env_file: str = ".env") -> bool:
    """
    Save session cookie to environment file.

    Args:
        cookie_value: The session cookie value
        env_file: Path to environment file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read existing .env file
        env_vars = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

        # Update session cookie
        env_vars["CLIO_SESSION_COOKIE"] = cookie_value

        # Write back to file
        with open(env_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

        logger.info(f"Session cookie saved to {env_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to save session cookie to {env_file}: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    session_manager = ClioSessionManager()

    # Try to get cookie from environment first
    cookie = session_manager.get_active_session_cookie()

    if not cookie:
        # If no cookie available, would need to fetch via browser
        email = input("Clio email: ")
        password = input("Clio password: ")
        cookie = session_manager.fetch_session_cookie(email, password)

        if cookie:
            # Save to .env for future use
            save_session_cookie_to_env(cookie)

    if cookie:
        # Test custom field set management
        field_manager = ClioCustomFieldSetManager(session_manager)

        # Example: Get field sets
        result = field_manager.get_custom_field_sets()
        print("Custom field sets result:", json.dumps(result, indent=2))
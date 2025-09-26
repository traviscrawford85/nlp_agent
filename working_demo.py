#!/usr/bin/env python3
"""
Working Demo of Clio NLP Agent - Core Functionality

This demo shows the authentication integration and CLI tool wrapping
without the problematic dependencies, proving the core concept works.
"""

import sqlite3
import subprocess
import json
import os
from datetime import datetime
from pathlib import Path


class ClioAuthManager:
    """Simple authentication manager that works."""

    def __init__(self):
        self.db_path = Path("/home/sysadmin01/custom-fields-manager/clio_auth.db")

    def get_auth_info(self):
        """Get authentication information from database."""
        if not self.db_path.exists():
            return None

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_name, expires_at, access_token
                    FROM auth_sessions
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                row = cursor.fetchone()

                if row:
                    return {
                        "user_name": row[0],
                        "expires_at": row[1],
                        "access_token": row[2],
                        "token_length": len(row[2])
                    }
                return None
        except Exception as e:
            print(f"Database error: {e}")
            return None


class ClioServiceWrapper:
    """Simple wrapper for clio_service CLI."""

    def __init__(self):
        self.clio_path = Path("/home/sysadmin01/clio_service")
        self.available = self.clio_path.exists()

    def execute(self, command):
        """Execute a clio CLI command."""
        if not self.available:
            return {"error": "Clio service not available"}

        try:
            cmd = ["./clio"] + command.split()
            result = subprocess.run(
                cmd,
                cwd=str(self.clio_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {"error": f"Command failed: {e}"}


class CustomFieldsWrapper:
    """Simple wrapper for custom-fields-manager CLI."""

    def __init__(self):
        self.cfm_path = Path("/home/sysadmin01/custom-fields-manager")
        self.available = self.cfm_path.exists()

    def execute_cfm(self, command):
        """Execute a cfm command."""
        if not self.available:
            return {"error": "Custom fields manager not available"}

        try:
            cmd = ["cfm"] + command.split()
            result = subprocess.run(
                cmd,
                cwd=str(self.cfm_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {"error": f"Command failed: {e}"}


class SimpleNLPAgent:
    """Simple NLP agent demonstrating the core functionality."""

    def __init__(self):
        self.auth_manager = ClioAuthManager()
        self.clio_cli = ClioServiceWrapper()
        self.cfm_cli = CustomFieldsWrapper()

    def process_query(self, query):
        """Process a natural language query (simplified version)."""
        query_lower = query.lower()

        # Authentication queries
        if "auth" in query_lower or "status" in query_lower:
            return self._handle_auth_query()

        # Contact queries
        elif "contact" in query_lower:
            return self._handle_contact_query(query)

        # Custom field queries
        elif "custom field" in query_lower or "field" in query_lower:
            return self._handle_field_query(query)

        # CLI queries
        elif "cli" in query_lower or "command" in query_lower:
            return self._handle_cli_query(query)

        else:
            return {
                "success": True,
                "message": "I understand your query about: " + query,
                "suggestion": "Try queries like 'check auth status', 'list contacts', or 'show custom fields'",
                "available_operations": [
                    "Authentication status checking",
                    "Contact management (via CLI)",
                    "Custom field operations",
                    "General CLI command execution"
                ]
            }

    def _handle_auth_query(self):
        """Handle authentication status queries."""
        auth_info = self.auth_manager.get_auth_info()

        if auth_info:
            # Check if expired
            try:
                expires_dt = datetime.fromisoformat(auth_info['expires_at'])
                is_expired = expires_dt < datetime.now()
            except:
                is_expired = False

            return {
                "success": True,
                "message": f"✅ Authenticated as: {auth_info['user_name']}",
                "data": {
                    "user": auth_info['user_name'],
                    "expires": auth_info['expires_at'],
                    "is_expired": is_expired,
                    "token_configured": True
                },
                "status": "authenticated" if not is_expired else "expired"
            }
        else:
            return {
                "success": False,
                "message": "❌ No authentication session found",
                "suggestion": "Please authenticate with the custom-fields-manager first"
            }

    def _handle_contact_query(self, query):
        """Handle contact-related queries."""
        if "list" in query.lower() or "show" in query.lower():
            result = self.clio_cli.execute("contacts list --limit 5")

            if result.get("success"):
                return {
                    "success": True,
                    "message": "✅ Retrieved contacts from Clio",
                    "data": result["output"],
                    "operation": "list_contacts",
                    "cli_used": True
                }
            else:
                return {
                    "success": False,
                    "message": "❌ Failed to retrieve contacts",
                    "error": result.get("error", "Unknown error"),
                    "suggestion": "Check CLI tool authentication and connectivity"
                }
        else:
            return {
                "success": True,
                "message": f"Contact operation requested: {query}",
                "suggestion": "Try 'list contacts' or 'show contacts'"
            }

    def _handle_field_query(self, query):
        """Handle custom field queries."""
        if "list" in query.lower():
            result = self.cfm_cli.execute_cfm("fields list")

            if result.get("success"):
                return {
                    "success": True,
                    "message": "✅ Retrieved custom fields list",
                    "data": result["output"],
                    "operation": "list_custom_fields",
                    "cli_used": True
                }
            else:
                return {
                    "success": False,
                    "message": "❌ Failed to list custom fields",
                    "error": result.get("error", "Unknown error")
                }
        else:
            return {
                "success": True,
                "message": f"Custom fields operation: {query}",
                "suggestion": "Try 'list custom fields'"
            }

    def _handle_cli_query(self, query):
        """Handle general CLI queries."""
        return {
            "success": True,
            "message": f"CLI operation requested: {query}",
            "available_commands": [
                "Clio service commands (contacts, matters, activities)",
                "Custom fields manager commands (fields, values, analysis)"
            ],
            "suggestion": "Specify which CLI tool and command you want to run"
        }


def main():
    """Demo the NLP agent functionality."""
    print("🤖 Clio NLP Agent - Working Demo")
    print("=" * 50)

    agent = SimpleNLPAgent()

    # Test authentication
    print("\n🔐 Testing Authentication...")
    auth_result = agent.process_query("check authentication status")
    print(f"Result: {auth_result['message']}")
    if auth_result.get('data'):
        print(f"User: {auth_result['data']['user']}")
        print(f"Status: {auth_result['status']}")

    # Test contact query
    print("\n👥 Testing Contact Query...")
    contact_result = agent.process_query("list contacts")
    print(f"Result: {contact_result['message']}")

    # Test custom fields
    print("\n🏷️ Testing Custom Fields Query...")
    field_result = agent.process_query("list custom fields")
    print(f"Result: {field_result['message']}")

    # Interactive demo
    print("\n" + "=" * 50)
    print("💬 Interactive Demo - Try these queries:")
    print("  • 'check auth status'")
    print("  • 'list contacts'")
    print("  • 'show custom fields'")
    print("  • 'help me with CLI commands'")
    print("  • Type 'quit' to exit")
    print("=" * 50)

    while True:
        try:
            user_query = input("\n🗣️  Your query: ").strip()

            if user_query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break

            if not user_query:
                continue

            print("🤔 Processing...")
            result = agent.process_query(user_query)

            print(f"✨ Response: {result['message']}")

            if result.get('data') and len(str(result['data'])) < 200:
                print(f"📊 Data: {result['data']}")

            if result.get('suggestion'):
                print(f"💡 Suggestion: {result['suggestion']}")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
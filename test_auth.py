#!/usr/bin/env python3
"""
Test script to verify Clio authentication token retrieval.

This script tests the auth manager functionality without starting the full server.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.auth_manager import ClioAuthManager, get_clio_auth_token, get_clio_session_info


def test_auth_retrieval():
    """Test authentication token retrieval from database."""
    print("=== Clio Authentication Test ===\n")

    # Test auth manager initialization
    auth_manager = ClioAuthManager()
    print(f"Database path: {auth_manager.db_path}")
    print(f"Database exists: {auth_manager.db_path.exists()}\n")

    # Test token retrieval
    print("Getting active token...")
    token = get_clio_auth_token()

    if token:
        print(f"✅ Token retrieved successfully")
        print(f"Token (first 20 chars): {token[:20]}...")
        print(f"Token length: {len(token)} characters\n")
    else:
        print("❌ No token found\n")
        return False

    # Test session info retrieval
    print("Getting session information...")
    session_info = get_clio_session_info()

    if session_info:
        print("✅ Session info retrieved successfully")
        print(f"User: {session_info.user_name}")
        print(f"User ID: {session_info.user_id}")
        print(f"Session ID: {session_info.session_id[:10]}...")
        print(f"Expires at: {session_info.expires_at}")
        print(f"Has refresh token: {bool(session_info.refresh_token)}")

        # Check if expired
        if session_info.expires_at:
            from datetime import datetime
            is_expired = session_info.expires_at < datetime.now()
            print(f"Is expired: {is_expired}")
        print()
    else:
        print("❌ No session info found\n")

    # List all sessions
    print("Listing all sessions...")
    sessions = auth_manager.list_all_sessions()
    print(f"Total sessions: {len(sessions)}")

    for i, session in enumerate(sessions[:3]):  # Show first 3
        print(f"  {i+1}. {session.user_name} - {session.session_id[:10]}... - {session.expires_at}")

    return True


def test_environment_override():
    """Test environment variable override."""
    print("\n=== Environment Variable Override Test ===\n")

    # Set environment variable
    os.environ["CLIO_AUTH_TOKEN"] = "test_env_token_12345"

    token = get_clio_auth_token()
    print(f"Token from environment: {token}")

    if token == "test_env_token_12345":
        print("✅ Environment variable override works")
    else:
        print("❌ Environment variable override failed")

    # Clean up
    del os.environ["CLIO_AUTH_TOKEN"]


if __name__ == "__main__":
    try:
        success = test_auth_retrieval()
        test_environment_override()

        if success:
            print("\n✅ Authentication system ready!")
            print("\nYou can now start the NLP agent with:")
            print("  cd clio-nlp-agent")
            print("  uvicorn main:app --reload")
        else:
            print("\n❌ Authentication setup incomplete")
            print("Make sure the Clio auth database exists and contains valid sessions")

    except Exception as e:
        print(f"\n❌ Error testing authentication: {e}")
        import traceback
        traceback.print_exc()
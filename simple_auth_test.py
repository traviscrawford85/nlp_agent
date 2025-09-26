#!/usr/bin/env python3
"""
Simple test script to verify Clio authentication token retrieval.
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime


def test_database_connection():
    """Test connection to the Clio auth database."""
    db_path = Path("/home/sysadmin01/custom-fields-manager/clio_auth.db")

    print("=== Clio Authentication Database Test ===\n")
    print(f"Database path: {db_path}")
    print(f"Database exists: {db_path.exists()}\n")

    if not db_path.exists():
        print("❌ Database not found!")
        return None

    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get the most recent session
            cursor.execute("""
                SELECT session_id, access_token, refresh_token, expires_at, user_id, user_name, created_at
                FROM auth_sessions
                ORDER BY created_at DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            if row:
                print("✅ Found authentication session:")
                print(f"  User: {row['user_name']}")
                print(f"  User ID: {row['user_id']}")
                print(f"  Session ID: {row['session_id'][:10]}...")
                print(f"  Created: {row['created_at']}")
                print(f"  Expires: {row['expires_at']}")
                print(f"  Token length: {len(row['access_token'])} chars")
                print(f"  Token preview: {row['access_token'][:20]}...")
                print(f"  Has refresh token: {bool(row['refresh_token'])}")

                # Check if expired
                if row['expires_at']:
                    try:
                        expires_dt = datetime.fromisoformat(row['expires_at'])
                        is_expired = expires_dt < datetime.now()
                        print(f"  Is expired: {is_expired}")
                    except ValueError:
                        print("  Expiration date format unknown")

                return row['access_token']
            else:
                print("❌ No authentication sessions found")
                return None

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return None


def test_token_retrieval():
    """Test the complete token retrieval process."""
    print("\n=== Token Retrieval Test ===\n")

    # First check environment variable
    env_token = os.getenv("CLIO_AUTH_TOKEN")
    if env_token:
        print(f"✅ Found token in environment variable")
        print(f"  Token length: {len(env_token)} chars")
        print(f"  Token preview: {env_token[:20]}...")
        return env_token
    else:
        print("ℹ️  No CLIO_AUTH_TOKEN environment variable set")

    # Then check database
    db_token = test_database_connection()
    if db_token:
        print("\n✅ Successfully retrieved token from database!")
        return db_token
    else:
        print("\n❌ Failed to retrieve token from database")
        return None


def main():
    """Main test function."""
    token = test_token_retrieval()

    if token:
        print("\n🎉 SUCCESS! Authentication is configured.")
        print("\nNext steps:")
        print("1. Make sure you have exported OPENAI_API_KEY:")
        print("   export OPENAI_API_KEY='your-openai-api-key'")
        print("2. Start the NLP agent:")
        print("   cd clio-nlp-agent")
        print("   uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        print("3. Test the agent:")
        print("   curl -X POST 'http://localhost:8000/nlp' \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"query\": \"Check my authentication status\"}'")
    else:
        print("\n❌ FAILED! No authentication token available.")
        print("\nTroubleshooting:")
        print("1. Make sure you're authenticated with the custom-fields-manager")
        print("2. Or set CLIO_AUTH_TOKEN environment variable manually")
        print("3. Check that the database file exists and is accessible")


if __name__ == "__main__":
    main()
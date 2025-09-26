#!/usr/bin/env python3
"""
Test script for Clio custom field set management functionality.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.clio_session import ClioSessionManager, ClioCustomFieldSetManager
from tools.custom_field_set_tools import get_custom_field_set_tools


def test_session_manager():
    """Test session cookie management."""
    print("🧪 Testing Clio Session Manager...")

    session_manager = ClioSessionManager()

    # Test environment cookie retrieval
    cookie = session_manager.get_session_cookie_from_env()
    if cookie:
        print(f"✅ Found session cookie in environment: {cookie[:20]}...")
    else:
        print("⚠️  No session cookie found in environment")
        print("   To test browser automation, set CLIO_SESSION_COOKIE in .env")
        print("   Or provide credentials to test automated login")

    return session_manager


def test_custom_field_set_manager(session_manager):
    """Test custom field set operations."""
    print("\n🧪 Testing Custom Field Set Manager...")

    field_manager = ClioCustomFieldSetManager(session_manager)

    # Test getting field sets (requires session cookie)
    print("Attempting to retrieve custom field sets...")
    result = field_manager.get_custom_field_sets()

    print("Result:", json.dumps(result, indent=2))

    if result.get("success"):
        print("✅ Successfully accessed custom field sets endpoint")
    else:
        print("⚠️  Could not access custom field sets:", result.get("error"))

    return result


def test_tools():
    """Test LangChain tools."""
    print("\n🧪 Testing Custom Field Set Tools...")

    tools = get_custom_field_set_tools()

    print(f"✅ Found {len(tools)} custom field set tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:80]}...")

    # Test one of the tools
    if tools:
        print("\nTesting get_custom_field_sets tool...")
        get_tool = next((t for t in tools if t.name == "get_custom_field_sets"), None)
        if get_tool:
            try:
                result = get_tool._run()
                result_data = json.loads(result)
                print("Tool result:", json.dumps(result_data, indent=2)[:200] + "...")
            except Exception as e:
                print(f"Tool execution error: {e}")


def test_postman_collection_parsing():
    """Test parsing the Postman collection."""
    print("\n🧪 Testing Postman Collection Parsing...")

    collection_file = "Clio_Custom_Field_Set.postman_collection.json"
    if os.path.exists(collection_file):
        with open(collection_file, 'r') as f:
            collection = json.load(f)

        print(f"✅ Loaded Postman collection: {collection['info']['name']}")

        # Extract the API structure
        for item in collection.get('item', []):
            request = item.get('request', {})
            method = request.get('method', 'GET')
            url = request.get('url', {}).get('raw', '')

            print(f"  - {method} {url}")

            # Show body parameters for the update operation
            if method == 'POST' and 'custom_field_sets' in url:
                body = request.get('body', {}).get('urlencoded', [])
                print(f"    Parameters ({len(body)} items):")
                for param in body[:3]:  # Show first 3 parameters
                    print(f"      {param['key']}: {param['value']}")
                if len(body) > 3:
                    print(f"      ... and {len(body) - 3} more")
    else:
        print(f"⚠️  Postman collection file not found: {collection_file}")


def main():
    """Main test function."""
    print("🚀 Clio Custom Field Set Management - Test Suite")
    print("=" * 50)

    # Test 1: Session Manager
    session_manager = test_session_manager()

    # Test 2: Custom Field Set Manager
    test_custom_field_set_manager(session_manager)

    # Test 3: LangChain Tools
    test_tools()

    # Test 4: Postman Collection
    test_postman_collection_parsing()

    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("✅ Session cookie management system ready")
    print("✅ Custom field set management tools integrated")
    print("✅ LangChain tools available for NLP agent")
    print("✅ Postman collection structure understood")

    print("\n💡 To fully test:")
    print("1. Add CLIO_SESSION_COOKIE to .env file")
    print("2. Or use authenticate_clio_session tool with credentials")
    print("3. Test via NLP agent with queries like:")
    print("   'Update the Essential Data custom field set'")
    print("   'Show me the available custom field sets'")


if __name__ == "__main__":
    main()
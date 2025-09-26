#!/usr/bin/env python3
"""
Setup verification script for Clio NLP Agent.

This script verifies that all components are working correctly without
requiring the full server to be running.
"""

import sys
import os
import sqlite3
from pathlib import Path
import subprocess
import json


def print_header(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")


def print_check(description, status, details=""):
    status_icon = "✅" if status else "❌"
    print(f"{status_icon} {description}")
    if details:
        for line in details.split('\n'):
            if line.strip():
                print(f"   {line}")


def check_authentication():
    """Check Clio authentication setup."""
    print_header("AUTHENTICATION CHECK")

    # Check environment variable
    env_token = os.getenv("CLIO_AUTH_TOKEN")
    if env_token:
        print_check("CLIO_AUTH_TOKEN environment variable", True,
                   f"Length: {len(env_token)} characters")
    else:
        print_check("CLIO_AUTH_TOKEN environment variable", False,
                   "Not set - will use database token")

    # Check database
    db_path = Path("/home/sysadmin01/custom-fields-manager/clio_auth.db")
    db_exists = db_path.exists()
    print_check("Clio auth database exists", db_exists,
               f"Path: {db_path}")

    if db_exists:
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_name, expires_at, access_token
                    FROM auth_sessions
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                row = cursor.fetchone()

                if row:
                    user_name, expires_at, token = row
                    print_check("Active authentication session found", True,
                               f"User: {user_name}\nExpires: {expires_at}\nToken length: {len(token)} chars")

                    # Check if expired
                    from datetime import datetime
                    try:
                        expires_dt = datetime.fromisoformat(expires_at)
                        is_expired = expires_dt < datetime.now()
                        print_check("Token is valid (not expired)", not is_expired,
                                   f"Expires: {expires_at}")
                    except:
                        print_check("Token expiration check", False, "Could not parse expiration date")
                else:
                    print_check("Authentication session", False, "No sessions found in database")

        except Exception as e:
            print_check("Database connection", False, f"Error: {e}")

    return db_exists


def check_openai():
    """Check OpenAI API key setup."""
    print_header("OPENAI API CHECK")

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print_check("OPENAI_API_KEY environment variable", True,
                   f"Length: {len(api_key)} characters\nStarts with: {api_key[:10]}...")

        # Basic format validation
        is_valid_format = api_key.startswith("sk-") and len(api_key) > 50
        print_check("API key format looks valid", is_valid_format,
                   "Starts with 'sk-' and has reasonable length")
        return True
    else:
        print_check("OPENAI_API_KEY environment variable", False,
                   "Not set - required for NLP functionality")
        return False


def check_cli_tools():
    """Check CLI tools availability."""
    print_header("CLI TOOLS CHECK")

    # Check clio_service
    clio_service_path = Path("/home/sysadmin01/clio_service")
    clio_exists = clio_service_path.exists()
    print_check("Clio service directory", clio_exists,
               f"Path: {clio_service_path}")

    if clio_exists:
        # Try to find the clio command
        clio_cmd = clio_service_path / "clio"
        if clio_cmd.exists():
            print_check("Clio CLI command", True, f"Found: {clio_cmd}")
        else:
            print_check("Clio CLI command", False, "clio command not found in directory")

    # Check custom-fields-manager
    cfm_path = Path("/home/sysadmin01/custom-fields-manager")
    cfm_exists = cfm_path.exists()
    print_check("Custom fields manager directory", cfm_exists,
               f"Path: {cfm_path}")

    if cfm_exists:
        # Check for cfm and clio-cfm commands
        commands_found = []
        for cmd in ["cfm", "clio-cfm"]:
            try:
                result = subprocess.run([cmd, "--help"],
                                      capture_output=True,
                                      text=True,
                                      timeout=5,
                                      cwd=str(cfm_path))
                if result.returncode == 0:
                    commands_found.append(cmd)
            except:
                pass

        if commands_found:
            print_check("Custom fields CLI commands", True,
                       f"Available: {', '.join(commands_found)}")
        else:
            print_check("Custom fields CLI commands", False,
                       "cfm/clio-cfm commands not accessible")

    return clio_exists and cfm_exists


def check_project_files():
    """Check project file structure."""
    print_header("PROJECT FILES CHECK")

    required_files = [
        "main.py",
        "agent.py",
        "requirements.txt",
        "README.md",
        "INSTRUCTIONS.md",
        "services/auth_manager.py",
        "services/rate_limiter.py",
        "tools/clio_api.py",
        "tools/clio_cli.py",
        "tools/custom_fields_cli.py",
        "models/requests.py",
        "models/responses.py",
    ]

    all_found = True
    for file_path in required_files:
        exists = Path(file_path).exists()
        print_check(f"File: {file_path}", exists)
        if not exists:
            all_found = False

    print_check("All required project files present", all_found)
    return all_found


def check_dependencies():
    """Check Python dependencies."""
    print_header("DEPENDENCIES CHECK")

    # Check Python version
    python_version = sys.version_info
    python_ok = python_version >= (3, 8)
    print_check(f"Python version", python_ok,
               f"Version: {python_version.major}.{python_version.minor}.{python_version.micro}")

    # Check key imports
    imports_to_check = [
        ("sqlite3", "Built-in SQLite support"),
        ("json", "Built-in JSON support"),
        ("pathlib", "Built-in Path support"),
        ("subprocess", "Built-in subprocess support"),
    ]

    optional_imports = [
        ("fastapi", "FastAPI web framework"),
        ("pydantic", "Data validation"),
        ("loguru", "Logging system"),
        ("httpx", "HTTP client"),
    ]

    all_core_available = True
    for module, description in imports_to_check:
        try:
            __import__(module)
            print_check(f"{description}", True, f"Module: {module}")
        except ImportError:
            print_check(f"{description}", False, f"Module: {module} not available")
            all_core_available = False

    print("\nOptional dependencies (install with 'pip install -r requirements.txt'):")
    for module, description in optional_imports:
        try:
            __import__(module)
            print_check(f"{description}", True, f"Module: {module}")
        except ImportError:
            print_check(f"{description}", False, f"Module: {module} not installed")

    return all_core_available


def provide_next_steps(auth_ok, openai_ok, cli_ok, files_ok, deps_ok):
    """Provide next steps based on checks."""
    print_header("NEXT STEPS")

    if not files_ok:
        print("❌ Missing project files - please ensure all files are present")
        return

    if not deps_ok:
        print("❌ Missing core Python dependencies - check Python installation")
        return

    if not auth_ok:
        print("❌ Authentication not configured:")
        print("   1. Make sure you're authenticated with custom-fields-manager")
        print("   2. Or set CLIO_AUTH_TOKEN environment variable manually")
        return

    if not openai_ok:
        print("❌ OpenAI API key not configured:")
        print("   export OPENAI_API_KEY='your-openai-api-key'")
        return

    if not cli_ok:
        print("⚠️  CLI tools not fully available - some features may not work")

    if auth_ok and openai_ok:
        print("🎉 READY TO START!")
        print("\n📋 To start the NLP agent:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Start the server: uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        print("   3. Test the agent: curl -X POST 'http://localhost:8000/nlp' \\")
        print("      -H 'Content-Type: application/json' \\")
        print("      -d '{\"query\": \"Check my authentication status\"}'")
        print("\n📖 For detailed usage instructions, see INSTRUCTIONS.md")


def main():
    """Main verification function."""
    print("🔍 Clio NLP Agent - Setup Verification")
    print("This script checks that all components are properly configured.")

    # Run all checks
    auth_ok = check_authentication()
    openai_ok = check_openai()
    cli_ok = check_cli_tools()
    files_ok = check_project_files()
    deps_ok = check_dependencies()

    # Summary
    provide_next_steps(auth_ok, openai_ok, cli_ok, files_ok, deps_ok)

    print(f"\n{'='*50}")
    total_checks = 5
    passed_checks = sum([auth_ok, openai_ok, cli_ok, files_ok, deps_ok])
    print(f"  VERIFICATION COMPLETE: {passed_checks}/{total_checks} checks passed")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
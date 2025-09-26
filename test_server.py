#!/usr/bin/env python3
"""
Test server to verify authentication integration without full dependencies.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our auth manager (simplified to avoid complex dependencies)
import sqlite3


def get_clio_auth_token():
    """Simple version of auth token retrieval."""
    # Try environment variable first
    env_token = os.getenv("CLIO_AUTH_TOKEN")
    if env_token:
        return env_token

    # Try database
    db_path = Path("/home/sysadmin01/custom-fields-manager/clio_auth.db")
    if not db_path.exists():
        return None

    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT access_token FROM auth_sessions
                ORDER BY created_at DESC LIMIT 1
            """)

            row = cursor.fetchone()
            return row['access_token'] if row else None

    except Exception:
        return None


def get_clio_session_info():
    """Get session information from database."""
    db_path = Path("/home/sysadmin01/custom-fields-manager/clio_auth.db")
    if not db_path.exists():
        return None

    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT session_id, access_token, refresh_token, expires_at, user_id, user_name
                FROM auth_sessions
                ORDER BY created_at DESC LIMIT 1
            """)

            row = cursor.fetchone()
            if row:
                return {
                    "session_id": row['session_id'],
                    "access_token": row['access_token'],
                    "refresh_token": row['refresh_token'],
                    "expires_at": row['expires_at'],
                    "user_id": row['user_id'],
                    "user_name": row['user_name']
                }
            return None

    except Exception:
        return None


# Create FastAPI app
app = FastAPI(title="Clio NLP Agent Test", version="1.0.0")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    services = {}

    # Check OpenAI API key
    if os.getenv("OPENAI_API_KEY"):
        services["openai"] = "configured"
    else:
        services["openai"] = "not_configured"

    # Check Clio auth token
    clio_token = get_clio_auth_token()
    if clio_token:
        session_info = get_clio_session_info()
        if session_info:
            try:
                expires_dt = datetime.fromisoformat(session_info['expires_at'])
                if expires_dt < datetime.now():
                    services["clio_auth"] = "expired"
                else:
                    services["clio_auth"] = f"authenticated_as_{session_info['user_name'].replace(' ', '_')}"
            except:
                services["clio_auth"] = "configured"
        else:
            services["clio_auth"] = "configured"
    else:
        services["clio_auth"] = "not_configured"

    # Check CLI tools
    if os.path.exists("/home/sysadmin01/clio_service"):
        services["clio_cli"] = "available"
    else:
        services["clio_cli"] = "not_found"

    if os.path.exists("/home/sysadmin01/custom-fields-manager"):
        services["custom_fields_cli"] = "available"
    else:
        services["custom_fields_cli"] = "not_found"

    status = "healthy" if all(
        s in ["healthy", "configured", "available"] or s.startswith("authenticated_as_")
        for s in services.values()
    ) else "degraded"

    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": services
    }


@app.get("/auth/status")
async def get_auth_status():
    """Get current authentication status."""
    try:
        session_info = get_clio_session_info()

        if not session_info:
            return {
                "authenticated": False,
                "message": "No authentication session found"
            }

        try:
            expires_dt = datetime.fromisoformat(session_info['expires_at'])
            is_expired = expires_dt < datetime.now()
        except:
            is_expired = False

        return {
            "authenticated": True,
            "user_name": session_info['user_name'],
            "user_id": session_info['user_id'],
            "session_id": session_info['session_id'][:8] + "...",
            "expires_at": session_info['expires_at'],
            "is_expired": is_expired,
            "has_refresh_token": bool(session_info['refresh_token']),
            "token_source": "database",
            "token_length": len(session_info['access_token'])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/nlp")
async def nlp_placeholder(request_data: dict):
    """Placeholder NLP endpoint showing authentication works."""
    token = get_clio_auth_token()

    if not token:
        return {
            "success": False,
            "message": "No Clio authentication token available. Please check authentication setup.",
            "suggestion": "Run 'python simple_auth_test.py' to diagnose authentication issues."
        }

    # Check OpenAI key
    if not os.getenv("OPENAI_API_KEY"):
        return {
            "success": False,
            "message": "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        }

    # Simulate successful processing
    query = request_data.get("query", "No query provided")

    return {
        "success": True,
        "message": f"✅ Authentication working! Your query '{query}' would be processed by the NLP agent.",
        "note": "This is a test response. Install full dependencies for complete functionality.",
        "auth_status": "authenticated",
        "token_available": True,
        "openai_configured": True
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Clio NLP Agent Test Server...")
    print("📋 Endpoints available:")
    print("   GET  /health      - Service health check")
    print("   GET  /auth/status - Authentication status")
    print("   POST /nlp         - Test NLP endpoint")
    print("   GET  /docs        - API documentation")

    uvicorn.run(app, host="0.0.0.0", port=8000)
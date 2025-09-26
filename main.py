"""
FastAPI application for Clio NLP Agent.

This module provides a REST API interface to the Clio NLP agent,
allowing natural language queries to be processed and converted
into Clio API calls and CLI commands.
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from agent import ClioNLPAgent
from models.requests import NLPRequest
from models.responses import (
    NLPResponse,
    ErrorResponse,
    HealthResponse,
    DetailedNLPResponse
)
from services.auth_manager import get_clio_auth_token, get_clio_session_info

# Global agent instance
agent: Optional[ClioNLPAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global agent

    # Startup
    logger.info("Starting Clio NLP Agent service...")

    try:
        # Get Clio auth token from database or environment
        clio_token = get_clio_auth_token()
        if clio_token:
            session_info = get_clio_session_info()
            if session_info:
                logger.info(f"Using Clio auth token for user: {session_info.user_name}")
            else:
                logger.info("Using Clio auth token from environment")
        else:
            logger.warning("No Clio auth token available - some features may not work")

        # Initialize the agent
        agent = ClioNLPAgent(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            clio_auth_token=clio_token,
            model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-16k"),
            temperature=float(os.getenv("AGENT_TEMPERATURE", "0.1"))
        )
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Clio NLP Agent service...")
    if agent:
        await agent.close()
    logger.info("Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Clio NLP Agent API",
    description="Natural Language Interface to Clio's API and CLI tools",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger.add("clio_nlp_agent.log", rotation="1 day", retention="7 days")


def get_agent() -> ClioNLPAgent:
    """Dependency to get the agent instance."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    services = {}

    # Check agent status
    if agent is not None:
        services["agent"] = "healthy"
    else:
        services["agent"] = "not_initialized"

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
            if session_info.expires_at and session_info.expires_at < datetime.utcnow():
                services["clio_auth"] = "expired"
            else:
                services["clio_auth"] = f"authenticated_as_{session_info.user_name.replace(' ', '_')}"
        else:
            services["clio_auth"] = "configured"
    else:
        services["clio_auth"] = "not_configured"

    # Check CLI tools availability
    clio_service_path = "/home/sysadmin01/clio_service"
    if os.path.exists(clio_service_path):
        services["clio_cli"] = "available"
    else:
        services["clio_cli"] = "not_found"

    custom_fields_path = "/home/sysadmin01/custom-fields-manager"
    if os.path.exists(custom_fields_path):
        services["custom_fields_cli"] = "available"
    else:
        services["custom_fields_cli"] = "not_found"

    status = "healthy" if all(
        s in ["healthy", "configured", "available"] for s in services.values()
    ) else "degraded"

    return HealthResponse(
        status=status,
        services=services
    )


@app.post("/nlp", response_model=DetailedNLPResponse)
async def process_nlp_query(
    request: NLPRequest,
    background_tasks: BackgroundTasks,
    current_agent: ClioNLPAgent = Depends(get_agent)
) -> DetailedNLPResponse:
    """
    Process a natural language query using the Clio NLP agent.

    This endpoint accepts natural language queries and converts them into
    appropriate Clio API calls or CLI commands, returning both structured
    data and human-readable explanations.
    """
    start_time = datetime.now()

    try:
        logger.info(f"Processing NLP query: {request.query[:100]}...")

        # Process the query using the agent
        result = await current_agent.process_query(
            query=request.query,
            context=request.context
        )

        execution_time = (datetime.now() - start_time).total_seconds()

        if result["success"]:
            # Parse structured data from agent result
            data = None
            raw_data = None

            # Try to extract structured data from agent response
            if "data" in result:
                data = result["data"]
                if request.include_raw_data:
                    raw_data = result.get("raw_data")

            # Create response
            response = DetailedNLPResponse(
                success=True,
                message=result.get("message", "Query processed successfully"),
                data=data,
                raw_data=raw_data if request.include_raw_data else None,
                operation_type=_extract_operation_type(request.query),
                entities_affected=_extract_affected_entities(result),
                execution_time=execution_time,
                agent_thoughts=result.get("agent_thoughts", []),
                tools_used=result.get("tools_used", []),
                confidence_score=_calculate_confidence_score(result)
            )

            # Log successful processing
            logger.info(f"Query processed successfully in {execution_time:.2f}s")

            return response

        else:
            # Handle agent errors
            error_message = result.get("error", "Unknown error occurred")
            logger.error(f"Agent error: {error_message}")

            return DetailedNLPResponse(
                success=False,
                message=f"Failed to process query: {error_message}",
                operation_type="error",
                execution_time=execution_time,
                agent_thoughts=result.get("agent_thoughts", []),
                tools_used=result.get("tools_used", []),
                warnings=[error_message]
            )

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        error_message = str(e)
        logger.error(f"Unexpected error processing query: {error_message}")

        return DetailedNLPResponse(
            success=False,
            message=f"Unexpected error: {error_message}",
            operation_type="error",
            execution_time=execution_time,
            warnings=[error_message]
        )


@app.get("/auth/status")
async def get_auth_status():
    """Get current authentication status and session information."""
    try:
        session_info = get_clio_session_info()

        if not session_info:
            return {
                "authenticated": False,
                "message": "No authentication session found"
            }

        is_expired = session_info.expires_at and session_info.expires_at < datetime.utcnow()

        return {
            "authenticated": True,
            "user_name": session_info.user_name,
            "user_id": session_info.user_id,
            "session_id": session_info.session_id[:8] + "...",  # Partial ID for security
            "expires_at": session_info.expires_at.isoformat() if session_info.expires_at else None,
            "is_expired": is_expired,
            "has_refresh_token": bool(session_info.refresh_token),
            "token_source": "database"
        }

    except Exception as e:
        logger.error(f"Error getting auth status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/token")
async def set_auth_token(
    token_data: Dict[str, str],
    current_agent: ClioNLPAgent = Depends(get_agent)
):
    """Set or update the Clio authentication token (overrides database token)."""
    try:
        token = token_data.get("token")
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")

        current_agent.set_clio_auth_token(token)
        logger.info("Clio auth token updated successfully (overriding database token)")

        return {
            "message": "Authentication token updated successfully",
            "note": "This overrides the database token for this session only"
        }

    except Exception as e:
        logger.error(f"Error updating auth token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_available_tools(current_agent: ClioNLPAgent = Depends(get_agent)):
    """List available tools and their descriptions."""
    try:
        tools_info = []

        for tool in current_agent.tools:
            tools_info.append({
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.args if hasattr(tool, 'args') else None
            })

        return {
            "tools": tools_info,
            "total_tools": len(tools_info)
        }

    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/examples")
async def get_query_examples():
    """Get example natural language queries that can be processed."""
    examples = [
        {
            "category": "Contact Management",
            "queries": [
                "Create a new contact named John Smith with email john@example.com",
                "Find all contacts with the last name 'Johnson'",
                "Update contact ID 12345 to change their email to newemail@example.com",
                "Search for contacts in the company 'Acme Corp'"
            ]
        },
        {
            "category": "Matter Management",
            "queries": [
                "Create a new matter for client ID 456 with description 'Personal Injury Case'",
                "Find all open matters for client John Doe",
                "List all matters created in the last month",
                "Show me matters with status 'Closed'"
            ]
        },
        {
            "category": "Time Tracking",
            "queries": [
                "Add 2 hours of work on matter 789 for contract review",
                "Show time entries for this week",
                "Create a time entry for 1.5 hours on matter 123 for client meeting",
                "Find all activities by user ID 999"
            ]
        },
        {
            "category": "Custom Fields",
            "queries": [
                "List all custom fields for contacts",
                "Show custom field values for contact ID 123",
                "Set the 'Priority' custom field to 'High' for matter 456",
                "Find all custom fields that are not being used"
            ]
        },
        {
            "category": "CLI Operations",
            "queries": [
                "Run a data sync for all contacts",
                "Generate a custom fields usage report",
                "Backup the custom fields database",
                "Check authentication status"
            ]
        }
    ]

    return {
        "examples": examples,
        "notes": [
            "Queries should be in natural language",
            "Be as specific as possible with IDs and parameters",
            "The agent will ask for clarification if needed",
            "Complex operations may be broken down into multiple steps"
        ]
    }


def _extract_operation_type(query: str) -> str:
    """Extract the type of operation from the query."""
    query_lower = query.lower()

    if any(word in query_lower for word in ["create", "add", "new"]):
        if "contact" in query_lower:
            return "create_contact"
        elif "matter" in query_lower:
            return "create_matter"
        elif "activity" in query_lower or "time" in query_lower:
            return "create_activity"
        else:
            return "create"
    elif any(word in query_lower for word in ["find", "search", "get", "list", "show"]):
        return "search"
    elif any(word in query_lower for word in ["update", "change", "modify"]):
        return "update"
    elif any(word in query_lower for word in ["delete", "remove"]):
        return "delete"
    else:
        return "unknown"


def _extract_affected_entities(result: Dict[str, Any]) -> list:
    """Extract information about entities that were affected."""
    entities = []

    # This would be enhanced to parse the actual result data
    # and extract entity information

    return entities


def _calculate_confidence_score(result: Dict[str, Any]) -> Optional[float]:
    """Calculate a confidence score for the result."""
    # Simple confidence calculation based on success and presence of data
    if not result.get("success", False):
        return 0.0

    score = 0.8  # Base score for successful execution

    # Boost score if we have structured data
    if result.get("data"):
        score += 0.1

    # Reduce score if there were warnings or errors in tool execution
    tools_used = result.get("tools_used", [])
    if tools_used:
        failed_tools = [t for t in tools_used if not t.get("success", True)]
        if failed_tools:
            score -= 0.2 * len(failed_tools) / len(tools_used)

    return max(0.0, min(1.0, score))


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP_{exc.status_code}",
            message=exc.detail
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="INTERNAL_SERVER_ERROR",
            message="An internal server error occurred"
        ).dict()
    )


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info"),
        access_log=True
    )
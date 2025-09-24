"""FastAPI application with Clio API constraints."""

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from nlp_agent import __version__
from nlp_agent.models.schemas import (
    HealthResponse,
    QueryRequest,
    QueryResponse,
    QueryListResponse,
    CLIRequest,
    CLIResponse,
    ErrorResponse,
    QueryStatus,
    PaginationInfo,
)
from nlp_agent.api.dependencies import get_query_service, get_cli_service
from nlp_agent.api.services import QueryService, CLIService

# Configure structured logging
logger = structlog.get_logger()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# FastAPI app
app = FastAPI(
    title="NLP Agent API",
    description="Type-safe NLP agent API with Clio constraints for natural language processing and CLI integration",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> ErrorResponse:
    """Global exception handler."""
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
    return ErrorResponse(
        error="internal_server_error",
        message="An internal server error occurred",
        timestamp=datetime.now(timezone.utc),
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=__version__,
    )


@app.post("/query", response_model=QueryResponse)
@limiter.limit("10/minute")  # Rate limiting
async def process_query(
    request: Request,
    query_request: QueryRequest,
    query_service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    """Process natural language query with rate limiting."""
    try:
        # Generate unique query ID
        query_id = str(uuid.uuid4())
        
        logger.info(
            "Processing query",
            query_id=query_id,
            query_length=len(query_request.query),
            user_ip=get_remote_address(request),
        )
        
        # Process the query
        result = await query_service.process_query(query_id, query_request)
        
        logger.info("Query processed successfully", query_id=query_id)
        return result
        
    except Exception as e:
        logger.error("Error processing query", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="query_processing_error",
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            ).model_dump(),
        )


@app.get("/queries", response_model=QueryListResponse)
async def list_queries(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    status: Optional[QueryStatus] = Query(None, description="Filter by query status"),
    created_after: Optional[datetime] = Query(None, description="Filter queries created after this timestamp"),
    query_service: QueryService = Depends(get_query_service),
) -> QueryListResponse:
    """List processed queries with pagination and filtering (Clio API constraint)."""
    try:
        # Apply filtering
        filters = {}
        if status:
            filters["status"] = status
        if created_after:
            filters["created_after"] = created_after
        
        # Get paginated results
        queries, total = await query_service.list_queries(
            page=page,
            limit=limit,
            filters=filters,
        )
        
        # Calculate pagination info
        pages = (total + limit - 1) // limit  # Ceiling division
        pagination = PaginationInfo(
            page=page,
            limit=limit,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )
        
        return QueryListResponse(queries=queries, pagination=pagination)
        
    except Exception as e:
        logger.error("Error listing queries", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="query_list_error",
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            ).model_dump(),
        )


@app.post("/cli/execute", response_model=CLIResponse)
@limiter.limit("5/minute")  # More restrictive rate limiting for CLI
async def execute_cli(
    request: Request,
    cli_request: CLIRequest,
    cli_service: CLIService = Depends(get_cli_service),
) -> CLIResponse:
    """Execute CLI command with rate limiting."""
    try:
        logger.info(
            "Executing CLI command",
            service=cli_request.service,
            command=cli_request.command,
            user_ip=get_remote_address(request),
        )
        
        result = await cli_service.execute_command(cli_request)
        
        logger.info(
            "CLI command executed",
            service=cli_request.service,
            command=cli_request.command,
            exit_code=result.exit_code,
        )
        
        return result
        
    except Exception as e:
        logger.error("Error executing CLI command", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="cli_execution_error",
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            ).model_dump(),
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
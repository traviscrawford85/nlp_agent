"""Service layer for API endpoints."""

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import structlog

from nlp_agent.models.schemas import (
    QueryRequest,
    QueryResponse,
    QueryStatus,
    CLIRequest,
    CLIResponse,
    QueryMetadata,
)
from nlp_agent.cli_integration.manager import CLIManager
from nlp_agent.nlp.processor import NLPProcessor

logger = structlog.get_logger()


class QueryService:
    """Service for processing natural language queries."""
    
    def __init__(self, nlp_processor: NLPProcessor, cli_manager: CLIManager):
        self.nlp_processor = nlp_processor
        self.cli_manager = cli_manager
        self._query_store: Dict[str, QueryResponse] = {}
    
    async def process_query(self, query_id: str, request: QueryRequest) -> QueryResponse:
        """Process a natural language query."""
        start_time = time.time()
        created_at = datetime.now(timezone.utc)
        
        # Create initial response
        response = QueryResponse(
            id=query_id,
            status=QueryStatus.PROCESSING,
            created_at=created_at,
        )
        
        # Store query
        self._query_store[query_id] = response
        
        try:
            # Process the natural language query
            processing_result = await self.nlp_processor.process_query(
                request.query,
                request.context or {},
                request.options or {},
            )
            
            # Update response with results
            response.status = QueryStatus.COMPLETED
            response.result = processing_result.get("result", {})
            response.api_calls = processing_result.get("api_calls", [])
            response.cli_calls = processing_result.get("cli_calls", [])
            response.completed_at = datetime.now(timezone.utc)
            
            # Add metadata if requested
            if request.options and request.options.include_metadata:
                processing_time = (time.time() - start_time) * 1000
                response.metadata = QueryMetadata(
                    processing_time_ms=processing_time,
                    tokens_used=processing_result.get("tokens_used"),
                    confidence_score=processing_result.get("confidence_score"),
                )
            
        except Exception as e:
            logger.error("Query processing failed", query_id=query_id, exc_info=e)
            response.status = QueryStatus.FAILED
            response.result = {"error": str(e)}
            response.completed_at = datetime.now(timezone.utc)
        
        # Update stored query
        self._query_store[query_id] = response
        return response
    
    async def list_queries(
        self,
        page: int,
        limit: int,
        filters: Optional[Dict] = None,
    ) -> Tuple[List[QueryResponse], int]:
        """List queries with pagination and filtering."""
        queries = list(self._query_store.values())
        
        # Apply filters
        if filters:
            if "status" in filters:
                queries = [q for q in queries if q.status == filters["status"]]
            if "created_after" in filters:
                queries = [q for q in queries if q.created_at >= filters["created_after"]]
        
        # Sort by creation date (newest first)
        queries.sort(key=lambda q: q.created_at, reverse=True)
        
        # Apply pagination
        total = len(queries)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_queries = queries[start_idx:end_idx]
        
        return paginated_queries, total


class CLIService:
    """Service for CLI command execution."""
    
    def __init__(self, cli_manager: CLIManager):
        self.cli_manager = cli_manager
    
    async def execute_command(self, request: CLIRequest) -> CLIResponse:
        """Execute a CLI command."""
        start_time = time.time()
        
        try:
            result = await self.cli_manager.execute_command(
                service=request.service,
                command=request.command,
                args=request.args or [],
                input_data=request.input_data,
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            return CLIResponse(
                stdout=result["stdout"],
                stderr=result["stderr"],
                exit_code=result["exit_code"],
                duration_ms=duration_ms,
                parsed_output=result.get("parsed_output"),
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("CLI command execution failed", exc_info=e)
            
            return CLIResponse(
                stdout="",
                stderr=str(e),
                exit_code=1,
                duration_ms=duration_ms,
            )
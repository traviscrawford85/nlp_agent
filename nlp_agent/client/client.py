"""Type-safe Python client for NLP Agent API."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
import structlog

from nlp_agent.models.schemas import (
    HealthResponse,
    QueryRequest,
    QueryResponse,
    QueryListResponse,
    CLIRequest,
    CLIResponse,
    ErrorResponse,
    QueryStatus,
)

logger = structlog.get_logger()


class NLPAgentClientError(Exception):
    """Base exception for NLP Agent client errors."""
    pass


class RateLimitError(NLPAgentClientError):
    """Rate limit exceeded error."""
    pass


class NLPAgentClient:
    """Type-safe Python client for NLP Agent API."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize the client.
        
        Args:
            base_url: Base URL of the NLP Agent API
            timeout: Request timeout in seconds
            headers: Additional headers to include in requests
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = headers or {}
        
        # Create HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self.headers,
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> httpx.Response:
        """Make an HTTP request with error handling."""
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        
        try:
            response = await self.client.request(method, url, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            
            # Handle other client/server errors
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        raise NLPAgentClientError(f"API error: {error_data['message']}")
                except ValueError:
                    pass
                
                response.raise_for_status()
            
            return response
            
        except httpx.RequestError as e:
            logger.error("Request failed", url=url, exc_info=e)
            raise NLPAgentClientError(f"Request failed: {e}")
    
    async def health_check(self) -> HealthResponse:
        """Check API health status."""
        response = await self._request("GET", "/health")
        return HealthResponse(**response.json())
    
    async def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        include_metadata: bool = False,
    ) -> QueryResponse:
        """Process a natural language query.
        
        Args:
            query: Natural language query to process
            context: Optional context for the query
            timeout: Query timeout in seconds
            include_metadata: Include processing metadata in response
            
        Returns:
            QueryResponse with processing results
        """
        options = {}
        if timeout is not None:
            options["timeout"] = timeout
        if include_metadata:
            options["include_metadata"] = include_metadata
        
        request = QueryRequest(
            query=query,
            context=context,
            options=options if options else None,
        )
        
        response = await self._request("POST", "/query", json=request.model_dump())
        return QueryResponse(**response.json())
    
    async def list_queries(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[QueryStatus] = None,
        created_after: Optional[datetime] = None,
    ) -> QueryListResponse:
        """List processed queries with pagination and filtering.
        
        Args:
            page: Page number (1-based)
            limit: Number of items per page
            status: Filter by query status
            created_after: Filter queries created after this timestamp
            
        Returns:
            QueryListResponse with paginated results
        """
        params = {"page": page, "limit": limit}
        
        if status:
            params["status"] = status.value
        if created_after:
            params["created_after"] = created_after.isoformat()
        
        response = await self._request("GET", "/queries", params=params)
        return QueryListResponse(**response.json())
    
    async def execute_cli(
        self,
        service: str,
        command: str,
        args: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> CLIResponse:
        """Execute a CLI command.
        
        Args:
            service: CLI service to execute
            command: Command to execute
            args: Command arguments
            input_data: JSON payload to pass to the command
            
        Returns:
            CLIResponse with execution results
        """
        request = CLIRequest(
            service=service,
            command=command,
            args=args,
            input_data=input_data,
        )
        
        response = await self._request("POST", "/cli/execute", json=request.model_dump())
        return CLIResponse(**response.json())


# Synchronous client wrapper
class SyncNLPAgentClient:
    """Synchronous wrapper for NLP Agent client."""
    
    def __init__(self, **kwargs):
        self._client_kwargs = kwargs
    
    def _run_async(self, coro):
        """Run async coroutine synchronously."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)
    
    def health_check(self) -> HealthResponse:
        """Check API health status (sync)."""
        async def _health_check():
            async with NLPAgentClient(**self._client_kwargs) as client:
                return await client.health_check()
        
        return self._run_async(_health_check())
    
    def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        include_metadata: bool = False,
    ) -> QueryResponse:
        """Process a natural language query (sync)."""
        async def _process_query():
            async with NLPAgentClient(**self._client_kwargs) as client:
                return await client.process_query(
                    query=query,
                    context=context,
                    timeout=timeout,
                    include_metadata=include_metadata,
                )
        
        return self._run_async(_process_query())
    
    def list_queries(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[QueryStatus] = None,
        created_after: Optional[datetime] = None,
    ) -> QueryListResponse:
        """List processed queries (sync)."""
        async def _list_queries():
            async with NLPAgentClient(**self._client_kwargs) as client:
                return await client.list_queries(
                    page=page,
                    limit=limit,
                    status=status,
                    created_after=created_after,
                )
        
        return self._run_async(_list_queries())
    
    def execute_cli(
        self,
        service: str,
        command: str,
        args: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> CLIResponse:
        """Execute a CLI command (sync)."""
        async def _execute_cli():
            async with NLPAgentClient(**self._client_kwargs) as client:
                return await client.execute_cli(
                    service=service,
                    command=command,
                    args=args,
                    input_data=input_data,
                )
        
        return self._run_async(_execute_cli())
"""
Rate limiting and pagination utilities for Clio API.

This module provides rate limiting, retry logic, and pagination handling
for Clio API requests to ensure compliance with API limits.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta

import httpx
from loguru import logger


class RateLimiter:
    """Rate limiter that respects Clio API limits and Retry-After headers."""

    def __init__(self, requests_per_minute: int = 300, requests_per_hour: int = 10000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.request_times: List[float] = []
        self._lock = asyncio.Lock()

    async def wait_if_needed(self):
        """Wait if we're approaching rate limits."""
        async with self._lock:
            now = time.time()

            # Remove requests older than 1 hour
            hour_ago = now - 3600
            self.request_times = [t for t in self.request_times if t > hour_ago]

            # Check hourly limit
            if len(self.request_times) >= self.requests_per_hour:
                sleep_time = 3600 - (now - self.request_times[0])
                logger.warning(f"Hourly rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)

            # Check per-minute limit
            minute_ago = now - 60
            recent_requests = [t for t in self.request_times if t > minute_ago]
            if len(recent_requests) >= self.requests_per_minute:
                sleep_time = 60 - (now - recent_requests[0])
                logger.warning(f"Per-minute rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)

            self.request_times.append(now)


class ClioAPIClient:
    """HTTP client with rate limiting, retries, and pagination for Clio API."""

    def __init__(self, base_url: str = "https://app.clio.com/api/v4", auth_token: str = None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.rate_limiter = RateLimiter()
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-API-VERSION": "4.0.9"
            }
        )

    def set_auth_token(self, token: str):
        """Set or update the authentication token."""
        self.auth_token = token
        self.client.headers["Authorization"] = f"Bearer {token}"

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> httpx.Response:
        """
        Make a rate-limited request to the Clio API with automatic retries.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON request body
            max_retries: Maximum number of retries

        Returns:
            httpx.Response object
        """
        if not self.auth_token:
            raise ValueError("Authentication token not set")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(max_retries + 1):
            try:
                await self.rate_limiter.wait_if_needed()

                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data
                )

                # Handle rate limiting with Retry-After header
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        sleep_time = int(retry_after)
                        logger.warning(f"Rate limited by server, sleeping for {sleep_time} seconds")
                        await asyncio.sleep(sleep_time)
                        continue

                # Handle other client/server errors with exponential backoff
                if response.status_code >= 400:
                    if attempt < max_retries and response.status_code >= 500:
                        sleep_time = 2 ** attempt
                        logger.warning(f"Server error {response.status_code}, retrying in {sleep_time}s")
                        await asyncio.sleep(sleep_time)
                        continue

                    response.raise_for_status()

                return response

            except httpx.RequestError as e:
                if attempt < max_retries:
                    sleep_time = 2 ** attempt
                    logger.warning(f"Request error: {e}, retrying in {sleep_time}s")
                    await asyncio.sleep(sleep_time)
                    continue
                raise

        raise httpx.HTTPError(f"Max retries ({max_retries}) exceeded")

    async def paginated_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        per_page: int = 50
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Make paginated requests to retrieve all results.

        Args:
            endpoint: API endpoint
            params: Query parameters
            per_page: Items per page (max 200 for Clio)

        Yields:
            Individual items from paginated results
        """
        if params is None:
            params = {}

        params["per_page"] = min(per_page, 200)  # Clio max is 200
        page = 1

        while True:
            params["page"] = page

            response = await self.request("GET", endpoint, params=params)
            data = response.json()

            # Handle different Clio response structures
            if "data" in data:
                items = data["data"] if isinstance(data["data"], list) else [data["data"]]
            else:
                # Some endpoints return items directly
                items = [data] if isinstance(data, dict) else data

            if not items:
                break

            for item in items:
                yield item

            # Check if there are more pages
            meta = data.get("meta", {})
            paging = meta.get("paging", {})

            if not paging.get("next"):
                break

            page += 1

    async def get_all(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        per_page: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all items from a paginated endpoint.

        Args:
            endpoint: API endpoint
            params: Query parameters
            per_page: Items per page

        Returns:
            List of all items
        """
        items = []
        async for item in self.paginated_request(endpoint, params, per_page):
            items.append(item)
        return items

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
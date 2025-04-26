"""
Linear API client for the MCP server.

This module provides the base client for interacting with the Linear API.
"""

import asyncio
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp
import backoff
import requests
from pydantic import BaseModel, Field

from src.utils.errors import LinearAPIError, NotFoundError, UnauthorizedError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AuthType(str, Enum):
    """Authentication types for Linear API."""

    API_KEY = "api_key"
    OAUTH = "oauth"


class LinearClientConfig(BaseModel):
    """Configuration for the Linear API client."""

    api_url: str = "https://api.linear.app/graphql"
    auth_type: AuthType = AuthType.API_KEY
    api_key: Optional[str] = None
    oauth_token: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 1
    rate_limit_per_hour: int = 8000
    concurrent_requests: int = 10


class LinearError(BaseModel):
    """Model for Linear API errors."""

    message: str
    locations: Optional[List[Dict[str, int]]] = None
    path: Optional[List[str]] = None
    extensions: Optional[Dict[str, Any]] = None


class LinearClient:
    """
    Base client for interacting with the Linear API.
    
    This class provides the core functionality for making GraphQL requests
    to the Linear API.
    """

    def __init__(self, config: LinearClientConfig):
        """
        Initialize the Linear API client.
        
        Args:
            config: Client configuration
        """
        self.config = config
        
        # Validate auth configuration
        if config.auth_type == AuthType.API_KEY and not config.api_key:
            raise ValueError("API key is required when auth_type is api_key")
        elif config.auth_type == AuthType.OAUTH and not config.oauth_token:
            raise ValueError("OAuth token is required when auth_type is oauth")
        
        # Setup rate limiting
        self.rate_limit_remaining = config.rate_limit_per_hour
        self.rate_limit_reset = time.time() + 3600  # 1 hour from now
        
        # Setup concurrency control
        self.request_semaphore = asyncio.Semaphore(config.concurrent_requests)
        
        logger.info(f"Linear client initialized with auth type: {config.auth_type}")

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for Linear API requests.
        
        Returns:
            Headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.config.auth_type == AuthType.API_KEY:
            headers["Authorization"] = self.config.api_key
        else:  # OAUTH
            headers["Authorization"] = f"Bearer {self.config.oauth_token}"
        
        return headers

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, aiohttp.ClientError),
        max_tries=3,
        jitter=backoff.full_jitter,
    )
    async def execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the Linear API.
        
        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Query response
            
        Raises:
            LinearAPIError: If the query fails
            UnauthorizedError: If authentication fails
            NotFoundError: If the resource is not found
        """
        if variables is None:
            variables = {}
        
        payload = {
            "query": query,
            "variables": variables,
        }
        
        headers = self._get_headers()
        
        # Check rate limits
        await self._check_rate_limits()
        
        # Use semaphore to limit concurrent requests
        async with self.request_semaphore:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.config.api_url, 
                        json=payload, 
                        headers=headers,
                        timeout=self.config.timeout,
                    ) as response:
                        # Update rate limit information
                        self._update_rate_limits(response)
                        
                        # Parse response
                        response_data = await response.json()
                        
                        # Check for errors
                        if response.status == 401:
                            logger.error("Unauthorized request to Linear API")
                            raise UnauthorizedError("Invalid Linear API credentials")
                        
                        if response.status == 404:
                            logger.error("Resource not found in Linear API")
                            raise NotFoundError("Resource not found in Linear API")
                        
                        if "errors" in response_data:
                            errors = [LinearError(**error) for error in response_data["errors"]]
                            error_messages = "; ".join(error.message for error in errors)
                            logger.error(f"Linear API errors: {error_messages}")
                            raise LinearAPIError(f"Linear API errors: {error_messages}")
                        
                        if response.status != 200:
                            logger.error(f"Linear API error: HTTP {response.status}")
                            raise LinearAPIError(f"Linear API error: HTTP {response.status}")
                        
                        return response_data["data"]
            
            except aiohttp.ClientError as e:
                logger.error(f"HTTP error making Linear API request: {e}")
                raise LinearAPIError(f"HTTP error: {e}")
            
            except asyncio.TimeoutError:
                logger.error("Timeout making Linear API request")
                raise LinearAPIError("Request timed out")
            
            except Exception as e:
                if isinstance(e, (UnauthorizedError, NotFoundError, LinearAPIError)):
                    raise
                logger.error(f"Unexpected error making Linear API request: {e}")
                raise LinearAPIError(f"Unexpected error: {e}")

    def _update_rate_limits(self, response: aiohttp.ClientResponse) -> None:
        """
        Update rate limit information from response headers.
        
        Args:
            response: API response
        """
        # Linear includes rate limit headers in the response
        if "X-RateLimit-Remaining" in response.headers:
            try:
                self.rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
            except (ValueError, TypeError):
                pass
        
        if "X-RateLimit-Reset" in response.headers:
            try:
                self.rate_limit_reset = int(response.headers["X-RateLimit-Reset"])
            except (ValueError, TypeError):
                pass

    async def _check_rate_limits(self) -> None:
        """
        Check rate limits and delay if necessary.
        
        Raises:
            LinearAPIError: If rate limit is exceeded
        """
        if self.rate_limit_remaining <= 0:
            # Check if reset time is in the future
            now = time.time()
            if self.rate_limit_reset > now:
                delay = self.rate_limit_reset - now
                logger.warning(f"Rate limit reached, delaying for {delay:.2f} seconds")
                
                if delay > 60:  # If delay is more than a minute, fail fast
                    raise LinearAPIError(
                        f"Rate limit exceeded, reset in {delay:.2f} seconds"
                    )
                
                await asyncio.sleep(delay + 1)  # Add a small buffer
            
            # Reset the limits if the reset time has passed
            else:
                self.rate_limit_remaining = self.config.rate_limit_per_hour
                self.rate_limit_reset = now + 3600

    async def paginate_query(
        self,
        query: str,
        variables: Dict[str, Any],
        path: List[str],
        cursor_path: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Paginate through a GraphQL query to get all results.
        
        Args:
            query: GraphQL query string
            variables: Variables for the query
            path: Path to the paginated field in the response
            cursor_path: Path to the pageInfo.endCursor field
            
        Returns:
            List of all results
        """
        if cursor_path is None:
            cursor_path = path + ["pageInfo", "endCursor"]
        
        all_results = []
        has_next_page = True
        after_cursor = None
        
        while has_next_page:
            # Update variables with cursor
            if after_cursor:
                variables["after"] = after_cursor
            
            # Execute query
            response = await self.execute_query(query, variables)
            
            # Extract data and pagination info
            data = response
            for p in path[:-1]:
                if p not in data:
                    logger.error(f"Path {p} not found in response")
                    break
                data = data[p]
            
            # Extract nodes
            if path[-1] in data:
                nodes = data[path[-1]]["nodes"]
                all_results.extend(nodes)
                
                # Check if there's a next page
                has_next_page = data[path[-1]]["pageInfo"]["hasNextPage"]
                
                # Get cursor for next page
                cursor_data = response
                for p in cursor_path[:-1]:
                    if p in cursor_data:
                        cursor_data = cursor_data[p]
                    else:
                        has_next_page = False
                        break
                
                if has_next_page and cursor_path[-1] in cursor_data:
                    after_cursor = cursor_data[cursor_path[-1]]
                else:
                    has_next_page = False
            else:
                has_next_page = False
        
        return all_results
"""
Unified search across Linear resource types.

This module provides functionality for searching across multiple 
Linear resource types with a single query.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, ValidationError

from src.linear.client import LinearClient
from src.search.cache import SearchCache
from src.search.engine import SearchEngine, SearchOptions, SearchResponse, SearchResult
from src.search.formatter import SearchResultFormatter
from src.search.optimizer import SearchOptimizer
from src.search.query import (
    QueryBuilder,
    ResourceType,
    SearchCondition,
    SearchQuery,
)
from src.utils.errors import LinearAPIError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class UnifiedSearchRequest(BaseModel):
    """Model for a unified search request."""
    
    query: str
    resource_types: Optional[List[ResourceType]] = None
    filters: Optional[List[SearchCondition]] = None
    limit: int = 25
    optimize: bool = True
    format: bool = True
    timeout: Optional[float] = None


class UnifiedSearchResponse(BaseModel):
    """Model for a unified search response."""
    
    results: List[Dict[str, Any]]
    total_count: int
    has_more: bool = False
    execution_time: float
    resource_type_counts: Dict[str, int] = Field(default_factory=dict)
    query: str


class UnifiedSearch:
    """
    Unified search across Linear resource types.
    
    This class provides a simplified interface for searching across
    multiple Linear resource types with a single query.
    """
    
    def __init__(
        self,
        search_engine: SearchEngine,
        optimizer: Optional[SearchOptimizer] = None,
        formatter: Optional[SearchResultFormatter] = None,
    ):
        """
        Initialize the unified search.
        
        Args:
            search_engine: Search engine for executing searches
            optimizer: Search optimizer for result optimization
            formatter: Search formatter for result formatting
        """
        self.search_engine = search_engine
        self.optimizer = optimizer or SearchOptimizer()
        self.formatter = formatter or SearchResultFormatter()
        logger.info("Unified search initialized")
    
    async def search(self, request: UnifiedSearchRequest) -> UnifiedSearchResponse:
        """
        Perform a unified search across multiple resource types.
        
        Args:
            request: Unified search request
            
        Returns:
            Unified search response
        """
        start_time = time.time()
        
        # Determine resource types to search
        resource_types = request.resource_types or [
            ResourceType.ISSUE,
            ResourceType.PROJECT,
            ResourceType.TEAM,
            ResourceType.USER,
        ]
        
        # Create search query
        query = SearchQuery(
            text=request.query,
            resource_types=resource_types,
            conditions=request.filters or [],
            limit=request.limit,
        )
        
        try:
            # Execute search
            search_timeout = request.timeout or self.search_engine.options.timeout
            response = await asyncio.wait_for(
                self.search_engine.search(query),
                timeout=search_timeout
            )
            
            # Optimize results if requested
            if request.optimize and not response.cache_hit:
                response = self.optimizer.optimize(response, query)
            
            # Format results if requested
            results = []
            if request.format:
                formatted_response = self.formatter.format_response(response)
                results = formatted_response.data["results"]
            else:
                results = [r.dict() for r in response.results]
            
            # Calculate counts by resource type
            resource_type_counts = {}
            for result in response.results:
                resource_type = result.type.value
                if resource_type not in resource_type_counts:
                    resource_type_counts[resource_type] = 0
                resource_type_counts[resource_type] += 1
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            return UnifiedSearchResponse(
                results=results,
                total_count=response.total_count,
                has_more=response.has_more,
                execution_time=execution_time,
                resource_type_counts=resource_type_counts,
                query=request.query,
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Unified search timed out after {search_timeout} seconds")
            raise LinearAPIError(
                code="TIMEOUT_ERROR",
                message=f"Search timed out after {search_timeout} seconds",
                details={"timeout": search_timeout}
            )
        
        except Exception as e:
            logger.error(f"Error in unified search: {e}")
            raise
    
    async def quick_search(
        self,
        query: str,
        limit: int = 10,
        resource_types: Optional[List[Union[ResourceType, str]]] = None,
    ) -> UnifiedSearchResponse:
        """
        Perform a quick search with minimal parameters.
        
        This is a convenience method for simple searches.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            resource_types: Resource types to search (optional)
            
        Returns:
            Unified search response
        """
        # Convert string resource types to enum if needed
        if resource_types:
            normalized_types = []
            for rt in resource_types:
                if isinstance(rt, str):
                    try:
                        normalized_types.append(ResourceType(rt.lower()))
                    except ValueError:
                        logger.warning(f"Unknown resource type: {rt}")
                else:
                    normalized_types.append(rt)
            resource_types = normalized_types
        
        # Create request
        request = UnifiedSearchRequest(
            query=query,
            resource_types=resource_types,
            limit=limit,
            optimize=True,
            format=True,
        )
        
        # Execute search
        return await self.search(request)
    
    async def search_by_type(
        self,
        query: str,
        resource_type: Union[ResourceType, str],
        filters: Optional[List[SearchCondition]] = None,
        limit: int = 25,
    ) -> UnifiedSearchResponse:
        """
        Search for a specific resource type.
        
        Args:
            query: Search query string
            resource_type: Resource type to search
            filters: Additional filters (optional)
            limit: Maximum number of results to return
            
        Returns:
            Unified search response
        """
        # Convert string resource type to enum if needed
        if isinstance(resource_type, str):
            try:
                resource_type = ResourceType(resource_type.lower())
            except ValueError:
                raise ValueError(f"Unknown resource type: {resource_type}")
        
        # Create request
        request = UnifiedSearchRequest(
            query=query,
            resource_types=[resource_type],
            filters=filters,
            limit=limit,
            optimize=True,
            format=True,
        )
        
        # Execute search
        return await self.search(request)
    
    def get_supported_resource_types(self) -> List[Dict[str, str]]:
        """
        Get a list of supported resource types.
        
        Returns:
            List of resource types with id and name
        """
        return [
            {"id": rt.value, "name": rt.name.replace("_", " ").title()}
            for rt in ResourceType
        ]
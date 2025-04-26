"""
Search engine for Linear resources.

This module provides functionality for searching Linear resources.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, validator

from src.linear.client import LinearClient
from src.search.cache import SearchCache, CacheOptions
from src.search.query import (
    Condition,
    Operator,
    QueryBuilder,
    ResourceType,
    SearchQuery,
    SortDirection,
    SortOption,
)
from src.utils.errors import LinearAPIError, ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SearchResult(BaseModel):
    """Model for a search result item."""

    id: str
    type: ResourceType
    title: str
    url: Optional[str] = None
    description: Optional[str] = None
    identifier: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    team: Optional[Dict[str, str]] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Model for a search response."""

    results: List[SearchResult]
    total_count: int
    has_more: bool = False
    cursor: Optional[str] = None
    query: SearchQuery
    execution_time: Optional[float] = None
    cache_hit: bool = False


class SearchOptions(BaseModel):
    """Options for search operations."""

    include_description: bool = True
    include_comments: bool = False
    include_archived: bool = False
    max_results_per_type: int = 100
    timeout: int = 30


class SearchEngine:
    """
    Search engine for Linear resources.
    
    This class provides functionality for searching Linear resources.
    """

    def __init__(
        self,
        linear_client: LinearClient,
        query_builder: Optional[QueryBuilder] = None,
        options: Optional[SearchOptions] = None,
        cache_options: Optional[CacheOptions] = None,
    ):
        """
        Initialize the search engine.
        
        Args:
            linear_client: Linear API client
            query_builder: Query builder
            options: Search options
            cache_options: Cache options
        """
        self.linear_client = linear_client
        self.query_builder = query_builder or QueryBuilder()
        self.options = options or SearchOptions()
        self.cache = SearchCache(options=cache_options)
        logger.info("Search engine initialized")

    async def search(self, query: Union[str, SearchQuery]) -> SearchResponse:
        """
        Search Linear resources.
        
        Args:
            query: Search query string or object
            
        Returns:
            Search response
            
        Raises:
            ValidationError: If the query is invalid
            LinearAPIError: If there is an error communicating with Linear
        """
        start_time = time.time()
        
        # Check cache first
        cached_response = self.cache.get(query)
        if cached_response:
            logger.info("Cache hit for query: %s", query if isinstance(query, str) else query.text)
            response = SearchResponse(**cached_response)
            response.cache_hit = True
            response.execution_time = time.time() - start_time
            return response
        
        # Parse query string if needed
        if isinstance(query, str):
            try:
                query = self.query_builder.parse_query_string(query)
            except ValidationError as e:
                logger.error(f"Error parsing query string: {e}")
                raise
        
        # Execute search for each resource type
        all_results = []
        total_count = 0
        has_more = False
        
        # Use asyncio.gather to search all resource types concurrently
        search_tasks = [
            self._search_resource_type(resource_type, query)
            for resource_type in query.resource_types
        ]
        
        try:
            # Wait for all search tasks to complete or timeout
            search_results = await asyncio.gather(*search_tasks)
            
            # Combine results from all resource types
            for result in search_results:
                if result:
                    all_results.extend(result["results"])
                    total_count += result["total_count"]
                    has_more = has_more or result["has_more"]
            
            # Sort results if needed
            if query.sort:
                all_results.sort(
                    key=lambda r: r.get(query.sort.field, ""),
                    reverse=query.sort.direction == SortDirection.DESC,
                )
            
            # Apply limit
            limited_results = all_results[:query.limit]
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            response = SearchResponse(
                results=limited_results,
                total_count=total_count,
                has_more=has_more or len(all_results) > query.limit,
                query=query,
                execution_time=execution_time,
            )
            
            # Cache response
            self.cache.set(query, response)
            
            logger.info(
                "Search completed with %d results in %.2f seconds (query: %s)",
                len(limited_results),
                execution_time,
                query.text,
            )
            
            return response
        
        except asyncio.TimeoutError:
            logger.error(f"Search timed out after {self.options.timeout} seconds")
            raise LinearAPIError("Search timed out")
        
        except Exception as e:
            logger.error(f"Error during search: {e}")
            if isinstance(e, (ValidationError, LinearAPIError)):
                raise
            raise LinearAPIError(f"Error during search: {e}")

    async def _search_resource_type(
        self, resource_type: ResourceType, query: SearchQuery
    ) -> Optional[Dict[str, Any]]:
        """
        Search a specific resource type.
        
        Args:
            resource_type: Resource type to search
            query: Search query
            
        Returns:
            Dictionary with results, total count, and more flag
        """
        try:
            # Build GraphQL filter
            filter_dict = self.query_builder.build_graphql_filter(
                resource_type, query.conditions
            )
            
            # Include/exclude archived resources
            if not self.options.include_archived:
                # Add archived: false to filter
                # Note: This is a simplification, actual implementation depends on
                # how Linear API handles archived resources for each type
                if resource_type == ResourceType.ISSUE:
                    filter_dict["state"] = filter_dict.get("state", {})
                    filter_dict["state"]["type"] = {"neq": "canceled"}
            
            # Build GraphQL query
            graphql_query, variables = self.query_builder.build_graphql_query(
                resource_type, filter_dict, query
            )
            
            # Execute query
            result = await self.linear_client.execute_query(graphql_query, variables)
            
            # Extract results
            query_name = {
                ResourceType.ISSUE: "issues",
                ResourceType.PROJECT: "projects",
                ResourceType.TEAM: "teams",
                ResourceType.USER: "users",
                ResourceType.COMMENT: "comments",
                ResourceType.LABEL: "issueLabels",
                ResourceType.CYCLE: "cycles",
                ResourceType.WORKFLOW_STATE: "workflowStates",
            }[resource_type]
            
            if not result.get(query_name):
                return {"results": [], "total_count": 0, "has_more": False}
            
            nodes = result[query_name]["nodes"]
            page_info = result[query_name]["pageInfo"]
            total_count = result[query_name]["totalCount"]
            
            # Convert nodes to search results
            search_results = []
            for node in nodes:
                search_result = self._node_to_search_result(node, resource_type)
                if search_result:
                    search_results.append(search_result)
            
            return {
                "results": search_results,
                "total_count": total_count,
                "has_more": page_info["hasNextPage"],
                "cursor": page_info["endCursor"],
            }
        
        except Exception as e:
            logger.error(f"Error searching {resource_type}: {e}")
            return None

    def _node_to_search_result(
        self, node: Dict[str, Any], resource_type: ResourceType
    ) -> Optional[SearchResult]:
        """
        Convert a GraphQL node to a search result.
        
        Args:
            node: GraphQL node
            resource_type: Resource type
            
        Returns:
            Search result, or None if conversion fails
        """
        try:
            # Extract title based on resource type
            title = ""
            if resource_type == ResourceType.ISSUE:
                title = node.get("title", "")
            else:
                title = node.get("name", "")
            
            # Extract description if requested
            description = None
            if self.options.include_description:
                description = node.get("description")
            
            # Extract team if available
            team = None
            if "team" in node and node["team"]:
                team = {
                    "id": node["team"].get("id"),
                    "name": node["team"].get("name"),
                    "key": node["team"].get("key"),
                }
            
            # Extract additional data
            additional_data = {}
            if resource_type == ResourceType.ISSUE:
                if "priority" in node:
                    additional_data["priority"] = node["priority"]
                if "estimate" in node:
                    additional_data["estimate"] = node["estimate"]
                if "state" in node and node["state"]:
                    additional_data["state"] = {
                        "id": node["state"].get("id"),
                        "name": node["state"].get("name"),
                        "color": node["state"].get("color"),
                        "type": node["state"].get("type"),
                    }
                if "assignee" in node and node["assignee"]:
                    additional_data["assignee"] = {
                        "id": node["assignee"].get("id"),
                        "name": node["assignee"].get("name"),
                    }
                if "labels" in node and "nodes" in node["labels"]:
                    additional_data["labels"] = [
                        {
                            "id": label.get("id"),
                            "name": label.get("name"),
                            "color": label.get("color"),
                        }
                        for label in node["labels"]["nodes"]
                    ]
            elif resource_type == ResourceType.USER:
                if "email" in node:
                    additional_data["email"] = node["email"]
                if "displayName" in node:
                    additional_data["display_name"] = node["displayName"]
                if "active" in node:
                    additional_data["active"] = node["active"]
            elif resource_type == ResourceType.PROJECT:
                if "state" in node:
                    additional_data["state"] = node["state"]
                if "startDate" in node:
                    additional_data["start_date"] = node["startDate"]
                if "targetDate" in node:
                    additional_data["target_date"] = node["targetDate"]
            
            return SearchResult(
                id=node["id"],
                type=resource_type,
                title=title,
                url=node.get("url"),
                description=description,
                identifier=node.get("identifier"),
                created_at=node.get("createdAt"),
                updated_at=node.get("updatedAt"),
                team=team,
                additional_data=additional_data,
            )
        
        except Exception as e:
            logger.error(f"Error converting node to search result: {e}")
            return None
            
    def invalidate_cache(self, resource_type: Optional[ResourceType] = None) -> None:
        """
        Invalidate cache for a specific resource type or all types.
        
        Args:
            resource_type: Resource type to invalidate (optional)
        """
        self.cache.invalidate(resource_type)
        logger.info(
            "Invalidated cache for %s",
            f"resource type: {resource_type.value}" if resource_type else "all resource types",
        )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache.stats()
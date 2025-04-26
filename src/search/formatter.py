"""
Format search results for MCP clients.

This module provides formatting functionality for search results.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from src.mcp.types import MCPResponse
from src.search.engine import SearchResult, SearchResponse
from src.search.query import ResourceType
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SearchResultFormatter:
    """Format search results for MCP clients."""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the formatter.
        
        Args:
            base_url: Base URL for Linear links (optional)
        """
        self.base_url = base_url
    
    def format_response(self, response: SearchResponse) -> MCPResponse:
        """
        Format a search response for MCP.
        
        Args:
            response: Search response to format
            
        Returns:
            MCP response with formatted results
        """
        formatted_results = [self.format_result(result) for result in response.results]
        
        mcp_response = MCPResponse(
            status="success",
            data={
                "results": formatted_results,
                "totalCount": response.total_count,
                "hasMore": response.has_more,
                "cursor": response.cursor,
                "query": self._format_query(response.query),
            },
        )
        
        return mcp_response
    
    def format_result(self, result: SearchResult) -> Dict[str, Any]:
        """
        Format a single search result.
        
        Args:
            result: Search result to format
            
        Returns:
            Formatted result
        """
        formatted = {
            "id": result.id,
            "type": result.type.value,
            "title": result.title,
        }
        
        # Add optional fields if they exist
        if result.url:
            formatted["url"] = result.url
        
        if result.description:
            formatted["description"] = result.description
        
        if result.identifier:
            formatted["identifier"] = result.identifier
        
        if result.created_at:
            formatted["createdAt"] = result.created_at
        
        if result.updated_at:
            formatted["updatedAt"] = result.updated_at
        
        if result.team:
            formatted["team"] = result.team
        
        # Format additional data based on resource type
        formatted.update(self._format_additional_data(result))
        
        # Standardize the normalized score for ranking
        formatted["score"] = self._calculate_score(result)
        
        return formatted
    
    def _format_additional_data(self, result: SearchResult) -> Dict[str, Any]:
        """
        Format additional data based on resource type.
        
        Args:
            result: Search result
            
        Returns:
            Formatted additional data
        """
        additional = {}
        
        if not result.additional_data:
            return additional
        
        if result.type == ResourceType.ISSUE:
            # Format issue-specific fields
            if "priority" in result.additional_data:
                additional["priority"] = result.additional_data["priority"]
            
            if "estimate" in result.additional_data:
                additional["estimate"] = result.additional_data["estimate"]
            
            if "state" in result.additional_data:
                additional["state"] = result.additional_data["state"]
            
            if "assignee" in result.additional_data:
                additional["assignee"] = result.additional_data["assignee"]
            
            if "labels" in result.additional_data:
                additional["labels"] = result.additional_data["labels"]
        
        elif result.type == ResourceType.USER:
            # Format user-specific fields
            if "email" in result.additional_data:
                additional["email"] = result.additional_data["email"]
            
            if "display_name" in result.additional_data:
                additional["displayName"] = result.additional_data["display_name"]
            
            if "active" in result.additional_data:
                additional["active"] = result.additional_data["active"]
        
        elif result.type == ResourceType.PROJECT:
            # Format project-specific fields
            if "state" in result.additional_data:
                additional["state"] = result.additional_data["state"]
            
            if "start_date" in result.additional_data:
                additional["startDate"] = result.additional_data["start_date"]
            
            if "target_date" in result.additional_data:
                additional["targetDate"] = result.additional_data["target_date"]
        
        return additional
    
    def _calculate_score(self, result: SearchResult) -> float:
        """
        Calculate a normalized score for the result.
        
        This score can be used for ranking results when multiple
        resource types are mixed. Higher is better.
        
        Args:
            result: Search result
            
        Returns:
            Normalized score between 0 and 1
        """
        # Start with a base score
        score = 0.5
        
        # Boost score based on recency (if available)
        if result.updated_at:
            try:
                updated_at = datetime.fromisoformat(result.updated_at.replace("Z", "+00:00"))
                now = datetime.now().astimezone()
                
                # Calculate days since update
                days_since_update = (now - updated_at).days
                
                # Boost for recent updates (max boost of 0.3 for very recent updates)
                recency_boost = max(0, 0.3 - (days_since_update * 0.01))
                score += recency_boost
            except (ValueError, TypeError):
                # If date parsing fails, don't apply recency boost
                pass
        
        # Resource type specific boosts
        if result.type == ResourceType.ISSUE:
            # Priority boost (if available)
            if "priority" in result.additional_data:
                # Higher priority (lower number) gets higher boost
                priority = result.additional_data["priority"]
                if priority is not None:
                    # Linear uses: 0=no priority, 1=urgent, 2=high, 3=medium, 4=low
                    priority_mapping = {0: 0.1, 1: 0.2, 2: 0.15, 3: 0.1, 4: 0.05}
                    score += priority_mapping.get(priority, 0)
        
        # Boost based on title length (prefer descriptive but concise titles)
        if result.title:
            title_length = len(result.title)
            if 20 <= title_length <= 100:
                score += 0.1
        
        # Cap score at 1.0
        return min(score, 1.0)
    
    def _format_query(self, query: Any) -> Dict[str, Any]:
        """
        Format the query parameters for the response.
        
        Args:
            query: Search query
            
        Returns:
            Formatted query parameters
        """
        return {
            "resourceTypes": [rt.value for rt in query.resource_types],
            "conditions": [
                {
                    "field": condition.field,
                    "operator": condition.operator.value,
                    "value": condition.value,
                }
                for condition in query.conditions
            ],
            "limit": query.limit,
            "sort": {
                "field": query.sort.field,
                "direction": query.sort.direction.value,
            } if query.sort else None,
            "cursor": query.cursor,
        }
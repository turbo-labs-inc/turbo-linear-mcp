"""
Search result optimizer.

This module provides optimization for search results, including
relevance scoring, deduplication, and response size limiting.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from src.search.engine import SearchResult, SearchResponse
from src.search.query import ResourceType, SearchQuery
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RelevanceConfig(BaseModel):
    """Configuration for relevance scoring."""
    
    title_weight: float = 2.0
    description_weight: float = 1.0
    identifier_weight: float = 1.5
    recency_weight: float = 1.0
    recency_decay_days: int = 30  # Days after which recency score is halved
    exact_match_boost: float = 1.5
    partial_match_boost: float = 1.2
    min_score: float = 0.1
    max_score: float = 1.0


class OptimizerConfig(BaseModel):
    """Configuration for search result optimizer."""
    
    enabled: bool = True
    relevance: RelevanceConfig = Field(default_factory=RelevanceConfig)
    deduplicate: bool = True
    max_results_per_type: int = 50
    max_total_results: int = 100
    trim_descriptions: bool = True
    max_description_length: int = 300
    include_score_details: bool = False


class SearchOptimizer:
    """
    Optimizer for search results.
    
    This class provides optimizations for search results, including:
    - Relevance scoring based on query terms
    - Deduplication of similar results
    - Result limiting by type and total
    - Response size optimization
    """
    
    def __init__(self, config: Optional[OptimizerConfig] = None):
        """
        Initialize the optimizer.
        
        Args:
            config: Optimizer configuration
        """
        self.config = config or OptimizerConfig()
        logger.info("Search optimizer initialized with config: %s", self.config)
    
    def optimize(self, response: SearchResponse, query: Optional[SearchQuery] = None) -> SearchResponse:
        """
        Optimize a search response.
        
        Args:
            response: Search response to optimize
            query: Original search query (optional)
            
        Returns:
            Optimized search response
        """
        if not self.config.enabled:
            return response
        
        # Get a mutable copy of results
        results = [result.dict() for result in response.results]
        
        # Score results for relevance if query is provided
        if query and query.text:
            results = self._score_results(results, query)
        
        # Deduplicate results if enabled
        if self.config.deduplicate:
            results = self._deduplicate_results(results)
        
        # Limit results by type and total
        results = self._limit_results(results)
        
        # Optimize response size
        results = self._optimize_response_size(results)
        
        # Create a new response with optimized results
        optimized_response = SearchResponse(
            results=[SearchResult(**result) for result in results],
            total_count=response.total_count,
            has_more=response.has_more or len(results) < len(response.results),
            cursor=response.cursor,
            query=response.query,
        )
        
        logger.info(
            "Optimized search response: %d results (from %d original)",
            len(results),
            len(response.results),
        )
        
        return optimized_response
    
    def _score_results(self, results: List[Dict[str, Any]], query: SearchQuery) -> List[Dict[str, Any]]:
        """
        Score results for relevance to the query.
        
        Args:
            results: Results to score
            query: Search query
            
        Returns:
            Scored results
        """
        if not query.text:
            return results
        
        # Extract query terms
        query_terms = self._extract_query_terms(query.text)
        
        # Score each result
        for result in results:
            score, details = self._calculate_relevance_score(result, query_terms)
            result["relevance_score"] = score
            
            if self.config.include_score_details:
                result["score_details"] = details
        
        # Sort by relevance score
        results.sort(key=lambda r: r.get("relevance_score", 0), reverse=True)
        
        return results
    
    def _extract_query_terms(self, query_text: str) -> List[str]:
        """
        Extract terms from query text.
        
        Args:
            query_text: Query text
            
        Returns:
            List of query terms
        """
        # Remove special characters and operators
        cleaned_text = re.sub(r'[^\w\s]', ' ', query_text)
        cleaned_text = re.sub(r'\b(AND|OR|NOT)\b', ' ', cleaned_text, flags=re.IGNORECASE)
        
        # Split into terms and remove empty strings
        terms = [term.lower() for term in cleaned_text.split() if term.strip()]
        
        return terms
    
    def _calculate_relevance_score(self, result: Dict[str, Any], query_terms: List[str]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate relevance score for a result.
        
        Args:
            result: Result to score
            query_terms: Query terms
            
        Returns:
            Tuple of (score, score details)
        """
        score_details = {
            "title_score": 0.0,
            "description_score": 0.0,
            "identifier_score": 0.0,
            "recency_score": 0.0,
            "exact_match_count": 0,
            "partial_match_count": 0,
        }
        
        # Score title matches
        title = result.get("title", "").lower()
        title_score = 0.0
        
        for term in query_terms:
            if term in title:
                title_score += self.config.relevance.exact_match_boost
                score_details["exact_match_count"] += 1
            else:
                # Check for partial matches
                for word in title.split():
                    if term in word or word in term:
                        title_score += self.config.relevance.partial_match_boost
                        score_details["partial_match_count"] += 1
                        break
        
        score_details["title_score"] = min(
            title_score / max(len(query_terms), 1), self.config.relevance.max_score
        )
        
        # Score description matches
        description = result.get("description", "").lower()
        description_score = 0.0
        
        for term in query_terms:
            if term in description:
                description_score += self.config.relevance.exact_match_boost
                score_details["exact_match_count"] += 1
            else:
                # Check for partial matches
                for word in description.split():
                    if term in word or word in term:
                        description_score += self.config.relevance.partial_match_boost
                        score_details["partial_match_count"] += 1
                        break
        
        score_details["description_score"] = min(
            description_score / max(len(query_terms) * 3, 1), self.config.relevance.max_score
        )
        
        # Score identifier matches
        identifier = result.get("identifier", "").lower()
        identifier_score = 0.0
        
        for term in query_terms:
            if term in identifier:
                identifier_score += self.config.relevance.exact_match_boost
                score_details["exact_match_count"] += 1
        
        score_details["identifier_score"] = min(
            identifier_score / max(len(query_terms), 1), self.config.relevance.max_score
        )
        
        # Score recency
        import datetime
        
        recency_score = 0.0
        updated_at = result.get("updated_at")
        
        if updated_at:
            try:
                # Parse ISO 8601 timestamp
                updated_time = datetime.datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                now = datetime.datetime.now(datetime.timezone.utc)
                
                # Calculate days since update
                days_since_update = (now - updated_time).days
                
                # Apply recency scoring (more recent = higher score)
                recency_factor = 2 ** (-days_since_update / self.config.relevance.recency_decay_days)
                recency_score = min(recency_factor, self.config.relevance.max_score)
            except (ValueError, TypeError):
                # Invalid date format
                pass
        
        score_details["recency_score"] = recency_score
        
        # Calculate final score as weighted sum
        final_score = (
            score_details["title_score"] * self.config.relevance.title_weight +
            score_details["description_score"] * self.config.relevance.description_weight +
            score_details["identifier_score"] * self.config.relevance.identifier_weight +
            score_details["recency_score"] * self.config.relevance.recency_weight
        )
        
        # Normalize to range [min_score, max_score]
        normalized_score = min(
            max(
                self.config.relevance.min_score,
                final_score / (
                    self.config.relevance.title_weight +
                    self.config.relevance.description_weight +
                    self.config.relevance.identifier_weight +
                    self.config.relevance.recency_weight
                )
            ),
            self.config.relevance.max_score
        )
        
        return normalized_score, score_details
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate similar results.
        
        Args:
            results: Results to deduplicate
            
        Returns:
            Deduplicated results
        """
        if not results:
            return results
        
        # Use a set to track seen titles and identifiers
        seen_titles = set()
        seen_identifiers = set()
        deduplicated = []
        
        for result in results:
            title = result.get("title", "").lower()
            identifier = result.get("identifier", "").lower()
            
            # Skip if we've seen this title or identifier
            if (title and title in seen_titles) or (identifier and identifier in seen_identifiers):
                continue
            
            # Add to deduplicated results
            deduplicated.append(result)
            
            # Add to seen sets
            if title:
                seen_titles.add(title)
            if identifier:
                seen_identifiers.add(identifier)
        
        logger.debug(
            "Deduplicated %d results to %d unique results",
            len(results),
            len(deduplicated)
        )
        
        return deduplicated
    
    def _limit_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Limit results by type and total.
        
        Args:
            results: Results to limit
            
        Returns:
            Limited results
        """
        if not results:
            return results
        
        # Group results by type
        results_by_type = {}
        for result in results:
            result_type = result.get("type", "other")
            if result_type not in results_by_type:
                results_by_type[result_type] = []
            results_by_type[result_type].append(result)
        
        # Limit results per type
        limited_results = []
        for result_type, type_results in results_by_type.items():
            limited_results.extend(type_results[:self.config.max_results_per_type])
        
        # Sort by relevance score if available, otherwise keep original order
        if any("relevance_score" in result for result in limited_results):
            limited_results.sort(key=lambda r: r.get("relevance_score", 0), reverse=True)
        
        # Limit total results
        limited_results = limited_results[:self.config.max_total_results]
        
        logger.debug(
            "Limited %d results to %d (max %d per type, %d total)",
            len(results),
            len(limited_results),
            self.config.max_results_per_type,
            self.config.max_total_results
        )
        
        return limited_results
    
    def _optimize_response_size(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize response size.
        
        Args:
            results: Results to optimize
            
        Returns:
            Optimized results
        """
        if not results or not self.config.trim_descriptions:
            return results
        
        for result in results:
            # Trim description if too long
            description = result.get("description")
            if description and len(description) > self.config.max_description_length:
                # Try to trim at a sentence boundary
                cutoff = min(self.config.max_description_length, len(description))
                
                # Look for a period, question mark, or exclamation point
                for i in range(cutoff - 5, max(0, cutoff - 40), -1):
                    if description[i] in ['.', '?', '!'] and i + 1 < len(description) and description[i + 1] == ' ':
                        cutoff = i + 1
                        break
                
                result["description"] = description[:cutoff].strip() + "..."
                result["description_truncated"] = True
        
        return results
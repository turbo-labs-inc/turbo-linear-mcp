"""
Cache for search results.

This module provides caching functionality for search results.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set, Union

from pydantic import BaseModel, Field

from src.search.engine import SearchResponse
from src.search.query import ResourceType, SearchQuery
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CacheEntry(BaseModel):
    """Model for a cache entry."""
    
    response: Dict[str, Any]
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
    resource_types: Set[str] = Field(default_factory=set)
    query_hash: str
    last_accessed: float = Field(default_factory=time.time)
    access_count: int = 0


class CacheOptions(BaseModel):
    """Options for the search cache."""
    
    enabled: bool = True
    ttl: int = 300  # Time to live in seconds (5 minutes)
    max_size: int = 100  # Maximum number of entries in cache
    respect_cache_control: bool = True  # Respect cache-control headers
    min_access_count: int = 2  # Minimum access count to keep in cache during cleanup


class SearchCache:
    """Cache for search results."""
    
    def __init__(self, options: Optional[CacheOptions] = None):
        """
        Initialize the cache.
        
        Args:
            options: Cache options
        """
        self.options = options or CacheOptions()
        self._cache: Dict[str, CacheEntry] = {}
        self._resource_index: Dict[str, Set[str]] = {}  # Resource type -> cache keys
        logger.info("Search cache initialized with options: %s", self.options)
    
    def get(self, query: Union[str, SearchQuery]) -> Optional[Dict[str, Any]]:
        """
        Get a response from the cache.
        
        Args:
            query: Search query or query string
            
        Returns:
            Cached response if found and valid, None otherwise
        """
        if not self.options.enabled:
            return None
        
        query_hash = self._hash_query(query)
        cache_key = query_hash
        
        if cache_key not in self._cache:
            return None
        
        entry = self._cache[cache_key]
        
        # Check if entry is expired
        if entry.expires_at is not None and time.time() > entry.expires_at:
            logger.debug("Cache entry expired for query: %s", query_hash)
            self._remove_entry(cache_key)
            return None
        
        # Update access stats
        entry.last_accessed = time.time()
        entry.access_count += 1
        
        logger.debug("Cache hit for query: %s (access count: %d)", query_hash, entry.access_count)
        return entry.response
    
    def set(
        self, 
        query: Union[str, SearchQuery], 
        response: Union[SearchResponse, Dict[str, Any]],
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set a response in the cache.
        
        Args:
            query: Search query or query string
            response: Response to cache
            ttl: Time to live in seconds (overrides default)
        """
        if not self.options.enabled:
            return
        
        # Check if cache is full
        if len(self._cache) >= self.options.max_size:
            self._cleanup()
        
        query_hash = self._hash_query(query)
        cache_key = query_hash
        
        # Convert response to dict if it's a SearchResponse
        if isinstance(response, SearchResponse):
            response_dict = response.dict()
        else:
            response_dict = response
        
        # Calculate expiration time
        cache_ttl = ttl if ttl is not None else self.options.ttl
        expires_at = time.time() + cache_ttl if cache_ttl > 0 else None
        
        # Extract resource types from query
        resource_types = set()
        if isinstance(query, SearchQuery):
            resource_types = {rt.value for rt in query.resource_types}
        
        # Create cache entry
        entry = CacheEntry(
            response=response_dict,
            created_at=time.time(),
            expires_at=expires_at,
            resource_types=resource_types,
            query_hash=query_hash,
        )
        
        # Add to cache
        self._cache[cache_key] = entry
        
        # Update resource index
        for resource_type in resource_types:
            if resource_type not in self._resource_index:
                self._resource_index[resource_type] = set()
            self._resource_index[resource_type].add(cache_key)
        
        logger.debug("Added entry to cache with key: %s", cache_key)
    
    def invalidate(self, resource_type: Optional[Union[ResourceType, str]] = None) -> None:
        """
        Invalidate cache entries for a specific resource type or all entries.
        
        Args:
            resource_type: Resource type to invalidate (optional, invalidates all if None)
        """
        if not self.options.enabled:
            return
        
        if resource_type is None:
            # Invalidate all entries
            self._cache.clear()
            self._resource_index.clear()
            logger.info("Invalidated all cache entries")
            return
        
        # Convert ResourceType enum to string if needed
        resource_type_str = resource_type.value if isinstance(resource_type, ResourceType) else resource_type
        
        if resource_type_str not in self._resource_index:
            return
        
        # Get cache keys for the resource type
        keys_to_remove = self._resource_index[resource_type_str].copy()
        
        # Remove entries from cache
        for key in keys_to_remove:
            self._remove_entry(key)
        
        logger.info("Invalidated %d cache entries for resource type: %s", len(keys_to_remove), resource_type_str)
    
    def _remove_entry(self, cache_key: str) -> None:
        """
        Remove a cache entry.
        
        Args:
            cache_key: Cache key to remove
        """
        if cache_key not in self._cache:
            return
        
        entry = self._cache[cache_key]
        
        # Remove from resource index
        for resource_type in entry.resource_types:
            if resource_type in self._resource_index and cache_key in self._resource_index[resource_type]:
                self._resource_index[resource_type].remove(cache_key)
                
                # Clean up empty sets
                if not self._resource_index[resource_type]:
                    del self._resource_index[resource_type]
        
        # Remove from cache
        del self._cache[cache_key]
    
    def _cleanup(self) -> None:
        """
        Clean up the cache when it's full.
        
        Removes entries based on:
        1. Expired entries first
        2. Least recently accessed entries
        3. Least frequently accessed entries
        """
        now = time.time()
        expired_keys = []
        
        # Find expired entries
        for key, entry in self._cache.items():
            if entry.expires_at is not None and now > entry.expires_at:
                expired_keys.append(key)
        
        # Remove expired entries
        for key in expired_keys:
            self._remove_entry(key)
            
        # If we've freed up enough space, return
        if len(self._cache) < self.options.max_size:
            logger.debug("Cleaned up %d expired cache entries", len(expired_keys))
            return
        
        # Sort remaining entries by access count and last accessed time
        entries = sorted(
            self._cache.items(),
            key=lambda item: (
                # Prioritize entries with higher access count
                item[1].access_count,
                # For entries with same access count, prioritize more recently accessed
                item[1].last_accessed
            )
        )
        
        # Remove entries with access count below threshold
        keys_to_remove = [
            key for key, entry in entries 
            if entry.access_count < self.options.min_access_count
        ]
        
        for key in keys_to_remove:
            self._remove_entry(key)
            
        # If we've freed up enough space, return
        if len(self._cache) < self.options.max_size:
            logger.debug("Cleaned up %d cache entries with low access count", len(keys_to_remove))
            return
        
        # Remove oldest entries until we're under the limit
        remaining_to_remove = len(self._cache) - self.options.max_size + 10  # Remove extra to avoid frequent cleanups
        
        # Sort by last accessed time
        entries = sorted(
            self._cache.items(),
            key=lambda item: item[1].last_accessed
        )
        
        keys_to_remove = [key for key, _ in entries[:remaining_to_remove]]
        
        for key in keys_to_remove:
            self._remove_entry(key)
            
        logger.debug("Cleaned up %d additional cache entries", len(keys_to_remove))
    
    def _hash_query(self, query: Union[str, SearchQuery]) -> str:
        """
        Generate a hash for a query.
        
        Args:
            query: Search query or query string
            
        Returns:
            Hash string
        """
        if isinstance(query, str):
            # Simple hash for query string
            return hashlib.md5(query.encode()).hexdigest()
        
        # Convert query to dict and serialize
        query_dict = query.dict()
        
        # Sort dict keys to ensure consistent serialization
        query_json = json.dumps(query_dict, sort_keys=True)
        
        return hashlib.md5(query_json.encode()).hexdigest()
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        now = time.time()
        
        # Count expired entries
        expired_count = sum(
            1 for entry in self._cache.values()
            if entry.expires_at is not None and now > entry.expires_at
        )
        
        # Count entries by resource type
        resource_counts = {
            resource_type: len(keys)
            for resource_type, keys in self._resource_index.items()
        }
        
        # Calculate average age
        avg_age = 0
        if self._cache:
            total_age = sum(now - entry.created_at for entry in self._cache.values())
            avg_age = total_age / len(self._cache)
        
        return {
            "total_entries": len(self._cache),
            "expired_entries": expired_count,
            "resource_counts": resource_counts,
            "avg_age_seconds": avg_age,
            "enabled": self.options.enabled,
            "max_size": self.options.max_size,
            "ttl": self.options.ttl,
        }
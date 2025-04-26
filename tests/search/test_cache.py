"""
Tests for the search cache.
"""

import time
import unittest
from unittest.mock import Mock, patch

from src.search.cache import CacheEntry, CacheOptions, SearchCache
from src.search.engine import SearchResponse
from src.search.query import ResourceType, SearchQuery


class TestSearchCache(unittest.TestCase):
    """Tests for the search cache."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache_options = CacheOptions(
            enabled=True,
            ttl=5,  # Short TTL for testing
            max_size=10,
            min_access_count=2,
        )
        self.cache = SearchCache(options=self.cache_options)
        
        # Create a mock query and response
        self.mock_query = SearchQuery(
            text="test query",
            resource_types=[ResourceType.ISSUE],
        )
        
        self.mock_response = {
            "results": [
                {
                    "id": "issue1",
                    "type": "issue",
                    "title": "Test Issue",
                }
            ],
            "total_count": 1,
            "has_more": False,
        }

    def test_set_and_get(self):
        """Test setting and getting a cache entry."""
        # Set a cache entry
        self.cache.set(self.mock_query, self.mock_response)
        
        # Get the cache entry
        cached = self.cache.get(self.mock_query)
        
        # Check that the entry was retrieved correctly
        self.assertIsNotNone(cached)
        self.assertEqual(cached["results"][0]["id"], "issue1")
        self.assertEqual(cached["total_count"], 1)
        self.assertFalse(cached["has_more"])

    def test_get_nonexistent(self):
        """Test getting a nonexistent cache entry."""
        # Try to get a cache entry that doesn't exist
        cached = self.cache.get("nonexistent query")
        
        # Check that the entry is None
        self.assertIsNone(cached)

    def test_expiration(self):
        """Test that cache entries expire."""
        # Set a cache entry with a short TTL
        self.cache.set(self.mock_query, self.mock_response, ttl=1)
        
        # Check that the entry exists
        cached = self.cache.get(self.mock_query)
        self.assertIsNotNone(cached)
        
        # Wait for the entry to expire
        time.sleep(1.1)
        
        # Check that the entry is now gone
        cached = self.cache.get(self.mock_query)
        self.assertIsNone(cached)

    def test_invalidate_all(self):
        """Test invalidating all cache entries."""
        # Set some cache entries
        self.cache.set(self.mock_query, self.mock_response)
        self.cache.set("another query", self.mock_response)
        
        # Invalidate all entries
        self.cache.invalidate()
        
        # Check that all entries are gone
        self.assertIsNone(self.cache.get(self.mock_query))
        self.assertIsNone(self.cache.get("another query"))

    def test_invalidate_resource_type(self):
        """Test invalidating cache entries by resource type."""
        # Set cache entries for different resource types
        query1 = SearchQuery(
            text="query1",
            resource_types=[ResourceType.ISSUE],
        )
        query2 = SearchQuery(
            text="query2",
            resource_types=[ResourceType.PROJECT],
        )
        query3 = SearchQuery(
            text="query3",
            resource_types=[ResourceType.ISSUE, ResourceType.PROJECT],
        )
        
        self.cache.set(query1, self.mock_response)
        self.cache.set(query2, self.mock_response)
        self.cache.set(query3, self.mock_response)
        
        # Invalidate entries for a specific resource type
        self.cache.invalidate(ResourceType.ISSUE)
        
        # Check that entries with the invalidated resource type are gone
        self.assertIsNone(self.cache.get(query1))
        self.assertIsNotNone(self.cache.get(query2))
        self.assertIsNone(self.cache.get(query3))  # This should be invalidated too because it contains ISSUE

    def test_cleanup_expired(self):
        """Test that cleanup removes expired entries."""
        # Set the cache to have a small max size
        self.cache.options.max_size = 3
        
        # Set some entries with a short TTL
        self.cache.set("query1", self.mock_response, ttl=1)
        self.cache.set("query2", self.mock_response)
        self.cache.set("query3", self.mock_response)
        
        # Wait for the first entry to expire
        time.sleep(1.1)
        
        # Add another entry to trigger cleanup
        self.cache.set("query4", self.mock_response)
        
        # Check that the expired entry was removed
        self.assertIsNone(self.cache.get("query1"))
        self.assertIsNotNone(self.cache.get("query2"))
        self.assertIsNotNone(self.cache.get("query3"))
        self.assertIsNotNone(self.cache.get("query4"))
        
        # Check that we still have 3 entries
        self.assertEqual(len(self.cache._cache), 3)

    def test_cleanup_lru(self):
        """Test that cleanup removes least recently used entries."""
        # Set the cache to have a small max size
        self.cache.options.max_size = 3
        
        # Set some entries
        self.cache.set("query1", self.mock_response)
        self.cache.set("query2", self.mock_response)
        self.cache.set("query3", self.mock_response)
        
        # Access entries to update their access time
        self.cache.get("query1")  # Access count: 1
        self.cache.get("query2")  # Access count: 1
        self.cache.get("query3")  # Access count: 1
        self.cache.get("query1")  # Access count: 2 (should be kept)
        self.cache.get("query2")  # Access count: 2 (should be kept)
        
        # Add another entry to trigger cleanup (total: 4, max: 3)
        # This should remove query3 which has access count 1
        self.cache.set("query4", self.mock_response)
        
        # Check that the least accessed entry was removed
        self.assertIsNotNone(self.cache.get("query1"))
        self.assertIsNotNone(self.cache.get("query2"))
        self.assertIsNone(self.cache.get("query3"))
        self.assertIsNotNone(self.cache.get("query4"))
        
        # Check that we still have 3 entries
        self.assertEqual(len(self.cache._cache), 3)

    def test_hash_query_string(self):
        """Test hashing a query string."""
        query_string = "test query"
        hash1 = self.cache._hash_query(query_string)
        hash2 = self.cache._hash_query(query_string)
        
        # Check that the hashes are deterministic
        self.assertEqual(hash1, hash2)
        
        # Check that different queries have different hashes
        other_hash = self.cache._hash_query("different query")
        self.assertNotEqual(hash1, other_hash)

    def test_hash_query_object(self):
        """Test hashing a query object."""
        hash1 = self.cache._hash_query(self.mock_query)
        hash2 = self.cache._hash_query(self.mock_query)
        
        # Check that the hashes are deterministic
        self.assertEqual(hash1, hash2)
        
        # Check that different queries have different hashes
        other_query = SearchQuery(
            text="different query",
            resource_types=[ResourceType.ISSUE],
        )
        other_hash = self.cache._hash_query(other_query)
        self.assertNotEqual(hash1, other_hash)

    def test_stats(self):
        """Test getting cache statistics."""
        # Set some entries
        self.cache.set("query1", self.mock_response)
        self.cache.set("query2", self.mock_response, ttl=1)
        
        # Wait for the second entry to expire
        time.sleep(1.1)
        
        # Get cache stats
        stats = self.cache.stats()
        
        # Check that the stats are correct
        self.assertEqual(stats["total_entries"], 2)
        self.assertEqual(stats["expired_entries"], 1)
        self.assertTrue("resource_counts" in stats)
        self.assertTrue("avg_age_seconds" in stats)
        self.assertEqual(stats["enabled"], True)
        self.assertEqual(stats["max_size"], 10)
        self.assertEqual(stats["ttl"], 5)

    def test_disabled_cache(self):
        """Test that a disabled cache doesn't store entries."""
        # Disable the cache
        self.cache.options.enabled = False
        
        # Set a cache entry
        self.cache.set(self.mock_query, self.mock_response)
        
        # Try to get the entry
        cached = self.cache.get(self.mock_query)
        
        # Check that the entry wasn't stored
        self.assertIsNone(cached)
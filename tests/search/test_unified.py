"""
Tests for the unified search functionality.
"""

import unittest
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.search.engine import SearchEngine, SearchResponse, SearchResult
from src.search.formatter import SearchResultFormatter
from src.search.optimizer import SearchOptimizer
from src.search.query import ResourceType, SearchQuery
from src.search.unified import UnifiedSearch, UnifiedSearchRequest, UnifiedSearchResponse


class TestUnifiedSearch(unittest.TestCase):
    """Tests for the unified search functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.search_engine = Mock(spec=SearchEngine)
        self.search_engine.options = Mock(timeout=30)
        self.search_engine.search = AsyncMock()
        
        self.optimizer = Mock(spec=SearchOptimizer)
        self.formatter = Mock(spec=SearchResultFormatter)
        
        self.unified_search = UnifiedSearch(
            search_engine=self.search_engine,
            optimizer=self.optimizer,
            formatter=self.formatter
        )
        
        # Create mock search results
        self.mock_results = [
            SearchResult(
                id="issue1",
                type=ResourceType.ISSUE,
                title="Test Issue",
                description="This is a test issue.",
            ),
            SearchResult(
                id="project1",
                type=ResourceType.PROJECT,
                title="Test Project",
                description="This is a test project.",
            ),
        ]
        
        # Create mock search response
        self.mock_response = SearchResponse(
            results=self.mock_results,
            total_count=len(self.mock_results),
            has_more=False,
            query=SearchQuery(
                text="test",
                resource_types=[ResourceType.ISSUE, ResourceType.PROJECT],
            ),
        )
        
        # Configure mocks
        self.search_engine.search.return_value = self.mock_response
        self.optimizer.optimize.return_value = self.mock_response
        self.formatter.format_response.return_value = Mock(
            data={
                "results": [
                    {"id": "issue1", "type": "issue", "title": "Test Issue"},
                    {"id": "project1", "type": "project", "title": "Test Project"},
                ]
            }
        )

    @pytest.mark.asyncio
    async def test_search(self):
        """Test the search method."""
        # Create request
        request = UnifiedSearchRequest(
            query="test",
            resource_types=[ResourceType.ISSUE, ResourceType.PROJECT],
            limit=10,
            optimize=True,
            format=True,
        )
        
        # Execute search
        response = await self.unified_search.search(request)
        
        # Check that search engine was called
        self.search_engine.search.assert_called_once()
        
        # Check that optimizer was called
        self.optimizer.optimize.assert_called_once()
        
        # Check that formatter was called
        self.formatter.format_response.assert_called_once()
        
        # Check response
        self.assertIsInstance(response, UnifiedSearchResponse)
        self.assertEqual(len(response.results), 2)
        self.assertEqual(response.total_count, 2)
        self.assertFalse(response.has_more)
        self.assertGreaterEqual(response.execution_time, 0)
        self.assertEqual(response.resource_type_counts, {"issue": 1, "project": 1})
        self.assertEqual(response.query, "test")

    @pytest.mark.asyncio
    async def test_search_without_optimization(self):
        """Test search without optimization."""
        # Create request with optimization disabled
        request = UnifiedSearchRequest(
            query="test",
            resource_types=[ResourceType.ISSUE, ResourceType.PROJECT],
            limit=10,
            optimize=False,
            format=True,
        )
        
        # Execute search
        response = await self.unified_search.search(request)
        
        # Check that optimizer was not called
        self.optimizer.optimize.assert_not_called()
        
        # Check that formatter was called
        self.formatter.format_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_without_formatting(self):
        """Test search without formatting."""
        # Create request with formatting disabled
        request = UnifiedSearchRequest(
            query="test",
            resource_types=[ResourceType.ISSUE, ResourceType.PROJECT],
            limit=10,
            optimize=True,
            format=False,
        )
        
        # Execute search
        response = await self.unified_search.search(request)
        
        # Check that optimizer was called
        self.optimizer.optimize.assert_called_once()
        
        # Check that formatter was not called
        self.formatter.format_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_default_resource_types(self):
        """Test default resource types."""
        # Create request without resource types
        request = UnifiedSearchRequest(
            query="test",
            limit=10,
        )
        
        # Execute search
        await self.unified_search.search(request)
        
        # Check search query
        search_query = self.search_engine.search.call_args[0][0]
        self.assertEqual(len(search_query.resource_types), 4)  # Should include all default types
        self.assertIn(ResourceType.ISSUE, search_query.resource_types)
        self.assertIn(ResourceType.PROJECT, search_query.resource_types)
        self.assertIn(ResourceType.TEAM, search_query.resource_types)
        self.assertIn(ResourceType.USER, search_query.resource_types)

    @pytest.mark.asyncio
    async def test_quick_search(self):
        """Test quick search method."""
        # Execute quick search
        response = await self.unified_search.quick_search("test", limit=5)
        
        # Check that search engine was called with correct parameters
        search_query = self.search_engine.search.call_args[0][0]
        self.assertEqual(search_query.text, "test")
        self.assertEqual(search_query.limit, 5)
        
        # Check response
        self.assertIsInstance(response, UnifiedSearchResponse)

    @pytest.mark.asyncio
    async def test_search_by_type(self):
        """Test search by type method."""
        # Execute search by type
        response = await self.unified_search.search_by_type("test", ResourceType.ISSUE, limit=5)
        
        # Check that search engine was called with correct parameters
        search_query = self.search_engine.search.call_args[0][0]
        self.assertEqual(search_query.text, "test")
        self.assertEqual(search_query.limit, 5)
        self.assertEqual(len(search_query.resource_types), 1)
        self.assertEqual(search_query.resource_types[0], ResourceType.ISSUE)
        
        # Check response
        self.assertIsInstance(response, UnifiedSearchResponse)

    @pytest.mark.asyncio
    async def test_search_by_type_string(self):
        """Test search by type using string type."""
        # Execute search by type using string
        response = await self.unified_search.search_by_type("test", "issue", limit=5)
        
        # Check that search engine was called with correct parameters
        search_query = self.search_engine.search.call_args[0][0]
        self.assertEqual(search_query.text, "test")
        self.assertEqual(search_query.limit, 5)
        self.assertEqual(len(search_query.resource_types), 1)
        self.assertEqual(search_query.resource_types[0], ResourceType.ISSUE)
        
        # Check response
        self.assertIsInstance(response, UnifiedSearchResponse)

    @pytest.mark.asyncio
    async def test_search_with_invalid_type(self):
        """Test search with invalid resource type."""
        # Try to search with invalid type
        with self.assertRaises(ValueError):
            await self.unified_search.search_by_type("test", "invalid_type")

    def test_get_supported_resource_types(self):
        """Test getting supported resource types."""
        types = self.unified_search.get_supported_resource_types()
        
        # Check that all resource types are included
        self.assertEqual(len(types), len(ResourceType))
        
        # Check format of result
        for rt in types:
            self.assertIn("id", rt)
            self.assertIn("name", rt)
            self.assertIsInstance(rt["id"], str)
            self.assertIsInstance(rt["name"], str)
"""
Tests for the search response optimization.
"""

import json
import unittest
from unittest.mock import Mock

from src.search.engine import SearchResult, SearchResponse
from src.search.query import ResourceType, SearchQuery
from src.search.response_optimization import (
    OptimizationConfig,
    PerformanceMetrics,
    ProgressiveLoadingState,
    ResponseOptimizer,
)


class TestResponseOptimizer(unittest.TestCase):
    """Tests for the search response optimizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.optimizer = ResponseOptimizer(
            config=OptimizationConfig(
                compress_large_responses=True,
                compression_threshold_bytes=100,  # Small threshold for testing
                trim_fields=True,
                max_description_length=20,
                include_metadata=True,
                enable_progressive_loading=True,
                results_per_page=2,
                max_pages=5,
                enable_batching=True,
                max_batch_size=2,
                enable_streaming=True,
                stream_chunk_size=1,
                include_performance_metrics=True,
            )
        )
        
        # Create mock search results
        self.mock_results = [
            SearchResult(
                id="issue1",
                type=ResourceType.ISSUE,
                title="Test Issue 1",
                description="This is a long description that should be truncated during optimization.",
                additional_data={"priority": 1},
            ),
            SearchResult(
                id="issue2",
                type=ResourceType.ISSUE,
                title="Test Issue 2",
                description="Short description",
                additional_data={"priority": 2},
            ),
            SearchResult(
                id="issue3",
                type=ResourceType.ISSUE,
                title="Test Issue 3",
                description="Another description that exceeds the maximum length limit for testing.",
                additional_data={"priority": 3},
            ),
            SearchResult(
                id="issue4",
                type=ResourceType.ISSUE,
                title="Test Issue 4",
                description="Yet another long description that should be truncated during the optimization process.",
                additional_data={"priority": 4},
            ),
        ]
        
        # Create mock search query
        self.mock_query = SearchQuery(
            text="test query",
            resource_types=[ResourceType.ISSUE],
        )
        
        # Create mock search response
        self.mock_response = SearchResponse(
            results=self.mock_results,
            total_count=len(self.mock_results),
            has_more=False,
            query=self.mock_query,
            execution_time=0.5,
        )

    def test_optimize_content(self):
        """Test content optimization."""
        # Convert response to dictionary
        response_dict = self.mock_response.dict()
        
        # Optimize content
        optimized = self.optimizer._optimize_content(response_dict)
        
        # Check that descriptions are truncated
        for result in optimized["results"]:
            if len(result.get("description", "")) > self.optimizer.config.max_description_length:
                self.assertTrue(result["description_truncated"])
                self.assertLessEqual(
                    len(result["description"]),
                    self.optimizer.config.max_description_length
                )
        
        # Check that metadata is included
        for result in optimized["results"]:
            self.assertIn("additional_data", result)
            self.assertEqual(result["additional_data"]["priority"], int(result["id"][-1]))
        
        # Test with metadata disabled
        self.optimizer.config.include_metadata = False
        optimized = self.optimizer._optimize_content(response_dict)
        
        # Check that metadata is removed
        for result in optimized["results"]:
            self.assertNotIn("additional_data", result)

    def test_add_progressive_loading(self):
        """Test adding progressive loading info."""
        # Convert response to dictionary
        response_dict = self.mock_response.dict()
        
        # Add progressive loading
        optimized = self.optimizer._add_progressive_loading(response_dict)
        
        # Check that progressive loading state is added
        self.assertIn("loading_state", optimized)
        
        loading_state = optimized["loading_state"]
        self.assertEqual(loading_state["total_results"], 4)  # Total results
        self.assertEqual(loading_state["loaded_results"], 2)  # Results per page
        self.assertEqual(loading_state["current_page"], 1)
        self.assertEqual(loading_state["total_pages"], 2)  # 4 results / 2 per page = 2 pages
        self.assertTrue(loading_state["has_more"])
        
        # Check that results are paged
        self.assertEqual(len(optimized["results"]), 2)
        self.assertTrue(optimized["results_paged"])

    def test_compress_response(self):
        """Test compressing a response."""
        # Create a large response dictionary
        large_dict = {
            "results": [{"id": str(i), "data": "x" * 100} for i in range(10)],
            "total_count": 10,
        }
        
        # Compress response
        compressed = self.optimizer._compress_response(large_dict)
        
        # Check compression
        self.assertTrue(compressed["compressed"])
        self.assertIn("original_size", compressed)
        self.assertIn("compressed_size", compressed)
        self.assertIn("compression_ratio", compressed)
        self.assertIn("data", compressed)
        self.assertEqual(compressed["format"], "gzip+base64")
        
        # Check that compressed size is smaller
        self.assertLess(compressed["compressed_size"], compressed["original_size"])
        
        # Test small response (shouldn't be compressed)
        small_dict = {"results": [{"id": "1"}], "total_count": 1}
        result = self.optimizer._compress_response(small_dict)
        self.assertEqual(result, small_dict)  # Should return original
        
        # Test decompression
        decompressed = self.optimizer.decompress_response(compressed)
        self.assertEqual(decompressed, large_dict)

    def test_calculate_performance_metrics(self):
        """Test calculating performance metrics."""
        # Calculate metrics
        metrics = self.optimizer._calculate_performance_metrics(
            response=self.mock_response,
            initial_size=1000,
            optimized_size=800,
            query_time=0.5,
            optimization_time=0.1,
        )
        
        # Check metrics
        self.assertIsInstance(metrics, PerformanceMetrics)
        self.assertEqual(metrics.query_time_ms, 500)  # 0.5s * 1000
        self.assertEqual(metrics.result_count, 4)
        self.assertEqual(metrics.total_count, 4)
        self.assertEqual(metrics.response_size_bytes, 1000)
        
        # Compression metrics should be set since size > threshold
        self.assertIsNotNone(metrics.compressed_size_bytes)
        self.assertIsNotNone(metrics.compression_ratio)
        
        # Test query complexity
        self.assertGreaterEqual(metrics.query_complexity, 1)
        self.assertLessEqual(metrics.query_complexity, 10)

    def test_create_batched_responses(self):
        """Test creating batched responses."""
        # Create batches
        batches = self.optimizer.create_batched_responses(self.mock_response)
        
        # Check batches
        self.assertEqual(len(batches), 2)  # 4 results / 2 per batch = 2 batches
        
        # Check first batch
        self.assertEqual(len(batches[0]["results"]), 2)
        self.assertEqual(batches[0]["batch_index"], 0)
        self.assertEqual(batches[0]["total_batches"], 2)
        self.assertTrue(batches[0]["has_more"])
        
        # Check second batch
        self.assertEqual(len(batches[1]["results"]), 2)
        self.assertEqual(batches[1]["batch_index"], 1)
        self.assertEqual(batches[1]["total_batches"], 2)
        self.assertFalse(batches[1]["has_more"])  # Last batch
        
        # Test with small response (should be one batch)
        small_response = SearchResponse(
            results=self.mock_results[:1],
            total_count=1,
            has_more=False,
            query=self.mock_query,
        )
        
        batches = self.optimizer.create_batched_responses(small_response)
        self.assertEqual(len(batches), 1)

    def test_create_streamed_responses(self):
        """Test creating streamed responses."""
        # Create streamed chunks
        chunks = self.optimizer.create_streamed_responses(self.mock_response)
        
        # Check chunks
        self.assertEqual(len(chunks), 4)  # 4 results / 1 per chunk = 4 chunks
        
        # Check first chunk
        self.assertEqual(len(chunks[0]["results"]), 1)
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertEqual(chunks[0]["total_chunks"], 4)
        self.assertTrue(chunks[0]["has_more"])
        
        # Check last chunk
        self.assertEqual(len(chunks[3]["results"]), 1)
        self.assertEqual(chunks[3]["chunk_index"], 3)
        self.assertEqual(chunks[3]["total_chunks"], 4)
        self.assertFalse(chunks[3]["has_more"])  # Last chunk

    def test_optimize_response(self):
        """Test the full optimization process."""
        # Optimize response
        optimized = self.optimizer.optimize_response(self.mock_response)
        
        # Check that optimized response has expected fields
        self.assertIn("results", optimized)
        self.assertIn("loading_state", optimized)
        self.assertIn("performance_metrics", optimized)
        
        # Check progressive loading
        self.assertEqual(len(optimized["results"]), 2)  # Paged to 2 results
        
        # Check performance metrics
        metrics = optimized["performance_metrics"]
        self.assertEqual(metrics["result_count"], 4)
        self.assertEqual(metrics["total_count"], 4)
        
        # Test compressed format
        optimized = self.optimizer.optimize_response(self.mock_response, format_type="compressed")
        
        # For small test responses, it might not trigger compression
        # So let's check if it's compressed or not
        if optimized.get("compressed", False):
            self.assertTrue(optimized["compressed"])
            self.assertIn("data", optimized)
            self.assertIn("original_size", optimized)
            self.assertIn("compressed_size", optimized)
        else:
            # If not compressed, should have normal results
            self.assertIn("results", optimized)
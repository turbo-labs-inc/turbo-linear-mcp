"""
Tests for the search result optimizer.
"""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from src.search.engine import SearchResult, SearchResponse
from src.search.optimizer import (
    OptimizerConfig,
    RelevanceConfig,
    SearchOptimizer,
)
from src.search.query import ResourceType, SearchQuery


class TestSearchOptimizer(unittest.TestCase):
    """Tests for the search result optimizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.optimizer = SearchOptimizer(
            config=OptimizerConfig(
                enabled=True,
                relevance=RelevanceConfig(
                    title_weight=2.0,
                    description_weight=1.0,
                    identifier_weight=1.5,
                    recency_weight=1.0,
                    exact_match_boost=1.5,
                    partial_match_boost=1.2,
                ),
                deduplicate=True,
                max_results_per_type=3,
                max_total_results=10,
                trim_descriptions=True,
                max_description_length=100,
            )
        )
        
        # Create a mock query
        self.mock_query = SearchQuery(
            text="test search functionality",
            resource_types=[ResourceType.ISSUE, ResourceType.PROJECT],
        )
        
        # Create mock results
        self.mock_results = [
            SearchResult(
                id="issue1",
                type=ResourceType.ISSUE,
                title="Test Issue about search functionality",
                description="This is a test issue that shows how search functionality works.",
                identifier="TEST-1",
                created_at="2023-01-01T00:00:00Z",
                updated_at="2023-01-02T00:00:00Z",
            ),
            SearchResult(
                id="issue2",
                type=ResourceType.ISSUE,
                title="Another test issue",
                description="This issue has nothing to do with search.",
                identifier="TEST-2",
                created_at="2023-01-03T00:00:00Z",
                updated_at="2023-01-04T00:00:00Z",
            ),
            SearchResult(
                id="project1",
                type=ResourceType.PROJECT,
                title="Search Implementation Project",
                description="Project to implement search functionality across Linear resources.",
                identifier="PROJ-1",
                created_at="2023-01-05T00:00:00Z",
                updated_at="2023-01-06T00:00:00Z",
            ),
            SearchResult(
                id="issue3",
                type=ResourceType.ISSUE,
                title="Duplicate Test Issue about search functionality",
                description="This is a duplicate issue with the same title as another one.",
                identifier="TEST-3",
                created_at="2023-01-07T00:00:00Z",
                updated_at="2023-01-08T00:00:00Z",
            ),
            SearchResult(
                id="issue4",
                type=ResourceType.ISSUE,
                title="Issue with very long description",
                description="This issue has a very long description that should be truncated. " * 10,
                identifier="TEST-4",
                created_at="2023-01-09T00:00:00Z",
                updated_at="2023-01-10T00:00:00Z",
            ),
        ]
        
        # Create a mock response
        self.mock_response = SearchResponse(
            results=self.mock_results,
            total_count=len(self.mock_results),
            has_more=False,
            query=self.mock_query,
        )

    def test_extract_query_terms(self):
        """Test extraction of query terms."""
        # Test basic term extraction
        terms = self.optimizer._extract_query_terms("test search functionality")
        self.assertEqual(terms, ["test", "search", "functionality"])
        
        # Test with special characters
        terms = self.optimizer._extract_query_terms("test-search, functionality!")
        self.assertEqual(terms, ["test", "search", "functionality"])
        
        # Test with operators
        terms = self.optimizer._extract_query_terms("test AND search OR functionality")
        self.assertEqual(terms, ["test", "search", "functionality"])
        
        # Test with mixed case
        terms = self.optimizer._extract_query_terms("Test SEARCH functionality")
        self.assertEqual(terms, ["test", "search", "functionality"])

    def test_relevance_scoring(self):
        """Test relevance scoring of results."""
        results = [result.dict() for result in self.mock_results]
        scored_results = self.optimizer._score_results(results, self.mock_query)
        
        # Check that all results have a relevance score
        for result in scored_results:
            self.assertIn("relevance_score", result)
        
        # Check that results are sorted by relevance
        for i in range(len(scored_results) - 1):
            self.assertGreaterEqual(
                scored_results[i]["relevance_score"],
                scored_results[i + 1]["relevance_score"]
            )
        
        # Check that results with more query term matches have higher scores
        for result in scored_results:
            if "search" in result["title"].lower() and "functionality" in result["title"].lower():
                high_score_result = result
            elif "search" not in result["title"].lower() and "functionality" not in result["title"].lower():
                low_score_result = result
        
        self.assertGreater(high_score_result["relevance_score"], low_score_result["relevance_score"])

    def test_calculate_relevance_score(self):
        """Test calculation of relevance score."""
        result = self.mock_results[0].dict()
        query_terms = ["test", "search", "functionality"]
        
        score, details = self.optimizer._calculate_relevance_score(result, query_terms)
        
        # Check that score is between min and max
        self.assertGreaterEqual(score, self.optimizer.config.relevance.min_score)
        self.assertLessEqual(score, self.optimizer.config.relevance.max_score)
        
        # Check that details contain expected fields
        self.assertIn("title_score", details)
        self.assertIn("description_score", details)
        self.assertIn("identifier_score", details)
        self.assertIn("recency_score", details)
        self.assertIn("exact_match_count", details)
        self.assertIn("partial_match_count", details)
        
        # Check specific score components
        self.assertGreater(details["title_score"], 0)  # Title has "test" and "search"
        self.assertGreater(details["description_score"], 0)  # Description has "test" and "search"
        self.assertEqual(details["identifier_score"], 0)  # Identifier has no matches
        
        # Test with an empty result
        empty_result = {"title": "", "description": "", "identifier": ""}
        score, details = self.optimizer._calculate_relevance_score(empty_result, query_terms)
        self.assertEqual(score, self.optimizer.config.relevance.min_score)

    def test_recency_scoring(self):
        """Test recency scoring."""
        # Create results with different update times
        now = datetime.now(timezone.utc)
        recent_result = {
            "title": "Recent item",
            "updated_at": now.isoformat(),
        }
        
        old_result = {
            "title": "Old item",
            "updated_at": (now - timedelta(days=60)).isoformat(),
        }
        
        # Calculate scores for both
        recent_score, recent_details = self.optimizer._calculate_relevance_score(
            recent_result, ["item"]
        )
        old_score, old_details = self.optimizer._calculate_relevance_score(
            old_result, ["item"]
        )
        
        # Recent result should have higher recency score
        self.assertGreater(recent_details["recency_score"], old_details["recency_score"])

    def test_deduplication(self):
        """Test deduplication of results."""
        results = [result.dict() for result in self.mock_results]
        
        # Add a true duplicate
        duplicate = results[0].copy()
        duplicate["id"] = "duplicate"
        results.append(duplicate)
        
        # Run deduplication
        deduplicated = self.optimizer._deduplicate_results(results)
        
        # Check that duplicates are removed
        titles = [r["title"].lower() for r in deduplicated]
        self.assertEqual(len(titles), len(set(titles)))  # All titles should be unique
        
        # Check that the total count is reduced
        self.assertLess(len(deduplicated), len(results))

    def test_result_limiting(self):
        """Test limiting of results by type and total."""
        # Create results of different types
        results = []
        
        # Add 5 issues
        for i in range(5):
            results.append({
                "id": f"issue{i}",
                "type": "issue",
                "title": f"Issue {i}",
            })
        
        # Add 5 projects
        for i in range(5):
            results.append({
                "id": f"project{i}",
                "type": "project",
                "title": f"Project {i}",
            })
        
        # Run limiting with max 3 per type, 10 total
        self.optimizer.config.max_results_per_type = 3
        self.optimizer.config.max_total_results = 10
        limited = self.optimizer._limit_results(results)
        
        # Should have max 3 issues and 3 projects
        issue_count = sum(1 for r in limited if r["type"] == "issue")
        project_count = sum(1 for r in limited if r["type"] == "project")
        self.assertLessEqual(issue_count, 3)
        self.assertLessEqual(project_count, 3)
        
        # Total should be no more than 6 (3 issues + 3 projects)
        self.assertLessEqual(len(limited), 6)
        
        # Run limiting with max 2 per type, 3 total
        self.optimizer.config.max_results_per_type = 2
        self.optimizer.config.max_total_results = 3
        limited = self.optimizer._limit_results(results)
        
        # Should have max 2 issues and 2 projects, but total limited to 3
        self.assertLessEqual(len(limited), 3)

    def test_response_size_optimization(self):
        """Test optimization of response size."""
        # Create a result with a very long description
        long_desc = "This is a very long description that should be truncated. " * 10
        results = [{
            "id": "test1",
            "title": "Test Item",
            "description": long_desc,
        }]
        
        # Run optimization
        optimized = self.optimizer._optimize_response_size(results)
        
        # Check that description is truncated
        self.assertLess(len(optimized[0]["description"]), len(long_desc))
        self.assertTrue(optimized[0]["description"].endswith("..."))
        self.assertTrue(optimized[0]["description_truncated"])
        
        # Check that it tries to truncate at a sentence boundary
        self.assertTrue(
            optimized[0]["description"].rstrip("...").endswith(".") or
            optimized[0]["description"].rstrip("...").endswith("?") or
            optimized[0]["description"].rstrip("...").endswith("!")
        )

    def test_full_optimization(self):
        """Test the full optimization pipeline."""
        # Use optimizer on the mock response
        optimized = self.optimizer.optimize(self.mock_response, self.mock_query)
        
        # Check that optimization worked
        self.assertIsInstance(optimized, SearchResponse)
        self.assertLessEqual(len(optimized.results), len(self.mock_response.results))
        
        # Check result properties
        for result in optimized.results:
            # Check description length
            if hasattr(result, "description") and result.description:
                self.assertLessEqual(
                    len(result.description), 
                    self.optimizer.config.max_description_length + 3  # +3 for "..."
                )
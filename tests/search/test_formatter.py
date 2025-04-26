"""
Tests for the search result formatter.
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from src.mcp.types import MCPResponse
from src.search.engine import SearchResult, SearchResponse
from src.search.formatter import SearchResultFormatter
from src.search.query import (
    FilterOperator,
    ResourceType,
    SearchCondition,
    SearchQuery,
    SortDirection,
    SortField,
)


class TestSearchResultFormatter(unittest.TestCase):
    """Tests for the search result formatter."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = SearchResultFormatter(base_url="https://linear.app")
        self.mock_query = SearchQuery(
            text="test query",
            resource_types=[ResourceType.ISSUE, ResourceType.PROJECT],
            conditions=[
                SearchCondition(
                    field="title",
                    operator=FilterOperator.CONTAINS,
                    value="test",
                )
            ],
            limit=10,
            sort=Mock(field="updatedAt", direction=SortDirection.DESC),
        )
        
        self.mock_results = [
            SearchResult(
                id="issue1",
                type=ResourceType.ISSUE,
                title="Test Issue 1",
                url="https://linear.app/issue/TEST-1",
                description="This is a test issue",
                identifier="TEST-1",
                created_at="2023-01-01T00:00:00Z",
                updated_at="2023-01-02T00:00:00Z",
                team={"id": "team1", "name": "Test Team"},
                additional_data={
                    "priority": 1,
                    "state": "In Progress",
                    "assignee": {"id": "user1", "name": "Test User"},
                },
            ),
            SearchResult(
                id="project1",
                type=ResourceType.PROJECT,
                title="Test Project 1",
                url="https://linear.app/project/PROJ-1",
                description="This is a test project",
                identifier="PROJ-1",
                created_at="2023-01-03T00:00:00Z",
                updated_at="2023-01-04T00:00:00Z",
                team={"id": "team1", "name": "Test Team"},
                additional_data={
                    "state": "Active",
                    "start_date": "2023-01-01",
                    "target_date": "2023-03-01",
                },
            ),
        ]
        
        self.mock_response = SearchResponse(
            results=self.mock_results,
            total_count=2,
            has_more=False,
            cursor=None,
            query=self.mock_query,
        )

    def test_format_response(self):
        """Test formatting a search response."""
        formatted = self.formatter.format_response(self.mock_response)
        
        self.assertIsInstance(formatted, MCPResponse)
        self.assertEqual(formatted.status, "success")
        self.assertEqual(len(formatted.data["results"]), 2)
        self.assertEqual(formatted.data["totalCount"], 2)
        self.assertEqual(formatted.data["hasMore"], False)
        self.assertIsNone(formatted.data["cursor"])
        self.assertEqual(formatted.data["query"]["resourceTypes"], ["issue", "project"])

    def test_format_result_issue(self):
        """Test formatting an issue result."""
        issue = self.mock_results[0]
        formatted = self.formatter.format_result(issue)
        
        self.assertEqual(formatted["id"], "issue1")
        self.assertEqual(formatted["type"], "issue")
        self.assertEqual(formatted["title"], "Test Issue 1")
        self.assertEqual(formatted["url"], "https://linear.app/issue/TEST-1")
        self.assertEqual(formatted["description"], "This is a test issue")
        self.assertEqual(formatted["identifier"], "TEST-1")
        self.assertEqual(formatted["createdAt"], "2023-01-01T00:00:00Z")
        self.assertEqual(formatted["updatedAt"], "2023-01-02T00:00:00Z")
        self.assertEqual(formatted["team"], {"id": "team1", "name": "Test Team"})
        self.assertEqual(formatted["priority"], 1)
        self.assertEqual(formatted["state"], "In Progress")
        self.assertEqual(formatted["assignee"], {"id": "user1", "name": "Test User"})
        self.assertIsInstance(formatted["score"], float)
        self.assertTrue(0 <= formatted["score"] <= 1)

    def test_format_result_project(self):
        """Test formatting a project result."""
        project = self.mock_results[1]
        formatted = self.formatter.format_result(project)
        
        self.assertEqual(formatted["id"], "project1")
        self.assertEqual(formatted["type"], "project")
        self.assertEqual(formatted["title"], "Test Project 1")
        self.assertEqual(formatted["url"], "https://linear.app/project/PROJ-1")
        self.assertEqual(formatted["description"], "This is a test project")
        self.assertEqual(formatted["identifier"], "PROJ-1")
        self.assertEqual(formatted["createdAt"], "2023-01-03T00:00:00Z")
        self.assertEqual(formatted["updatedAt"], "2023-01-04T00:00:00Z")
        self.assertEqual(formatted["team"], {"id": "team1", "name": "Test Team"})
        self.assertEqual(formatted["state"], "Active")
        self.assertEqual(formatted["startDate"], "2023-01-01")
        self.assertEqual(formatted["targetDate"], "2023-03-01")
        self.assertIsInstance(formatted["score"], float)
        self.assertTrue(0 <= formatted["score"] <= 1)

    def test_calculate_score(self):
        """Test score calculation for results."""
        # Create a result with recent update
        result_recent = SearchResult(
            id="issue1",
            type=ResourceType.ISSUE,
            title="Test Issue with good length for scoring",
            updated_at=datetime.now().isoformat(),
            additional_data={"priority": 1},
        )
        
        # Create a result with old update
        old_date = "2020-01-01T00:00:00Z"
        result_old = SearchResult(
            id="issue2",
            type=ResourceType.ISSUE,
            title="Old",
            updated_at=old_date,
            additional_data={"priority": 4},
        )
        
        score_recent = self.formatter._calculate_score(result_recent)
        score_old = self.formatter._calculate_score(result_old)
        
        # Recent update should have higher score
        self.assertGreater(score_recent, score_old)

    def test_format_query(self):
        """Test formatting query parameters."""
        formatted = self.formatter._format_query(self.mock_query)
        
        self.assertEqual(formatted["resourceTypes"], ["issue", "project"])
        self.assertEqual(len(formatted["conditions"]), 1)
        self.assertEqual(formatted["conditions"][0]["field"], "title")
        self.assertEqual(formatted["conditions"][0]["operator"], "contains")
        self.assertEqual(formatted["conditions"][0]["value"], "test")
        self.assertEqual(formatted["limit"], 10)
        self.assertEqual(formatted["sort"]["field"], "updatedAt")
        self.assertEqual(formatted["sort"]["direction"], "desc")
        self.assertIsNone(formatted["cursor"])
"""
Tests for the advanced result formatter.
"""

import unittest
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
from src.search.result_formatter import (
    FormattingOptions,
    GroupingOptions,
    HighlightOptions,
    ResultFormatter,
    SummarizationOptions,
)


class TestResultFormatter(unittest.TestCase):
    """Tests for the advanced result formatter."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_formatter = Mock(spec=SearchResultFormatter)
        self.base_formatter.format_response.return_value = MCPResponse(
            status="success",
            data={
                "results": [
                    {
                        "id": "issue1",
                        "type": "issue",
                        "title": "Test Issue about search functionality",
                        "description": "We need to implement search functionality with multiple resource types.",
                        "url": "https://linear.app/issue/TEST-1",
                        "createdAt": "2023-01-01T00:00:00Z",
                        "updatedAt": "2023-01-02T00:00:00Z",
                    },
                    {
                        "id": "project1",
                        "type": "project",
                        "title": "Search Implementation Project",
                        "description": "Project to implement search functionality across Linear resources.",
                        "url": "https://linear.app/project/PROJ-1",
                        "createdAt": "2023-01-03T00:00:00Z",
                        "updatedAt": "2023-01-04T00:00:00Z",
                        "startDate": "2023-01-01T00:00:00Z",
                        "targetDate": "2023-03-01T00:00:00Z",
                    },
                ],
                "totalCount": 2,
                "hasMore": False,
                "cursor": None,
                "query": {
                    "resourceTypes": ["issue", "project"],
                    "conditions": [
                        {
                            "field": "title",
                            "operator": "contains",
                            "value": "search",
                        }
                    ],
                    "limit": 10,
                    "sort": {"field": "updatedAt", "direction": "desc"},
                    "cursor": None,
                },
            },
        )
        
        self.mock_query = SearchQuery(
            text="search functionality",
            resource_types=[ResourceType.ISSUE, ResourceType.PROJECT],
            conditions=[
                SearchCondition(
                    field="title",
                    operator=FilterOperator.CONTAINS,
                    value="search",
                )
            ],
            limit=10,
            sort=Mock(field="updatedAt", direction=SortDirection.DESC),
        )
        
        self.mock_response = Mock(spec=SearchResponse)
        
        # Different formatting options for testing
        self.default_options = FormattingOptions()
        
        self.highlight_options = FormattingOptions(
            highlights=HighlightOptions(
                enabled=True,
                tag_open="<mark>",
                tag_close="</mark>",
                max_fragments=2,
                fragment_size=50,
            )
        )
        
        self.grouping_options = FormattingOptions(
            grouping=GroupingOptions(
                enabled=True,
                field="type",
            )
        )
        
        self.summarization_options = FormattingOptions(
            summarization=SummarizationOptions(
                enabled=True,
                max_length=20,
            )
        )

    def test_format_response_default(self):
        """Test formatting with default options."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.default_options,
        )
        
        result = formatter.format_response(self.mock_response, self.mock_query)
        
        # Should call base formatter
        self.base_formatter.format_response.assert_called_once_with(self.mock_response)
        
        # Should return a dictionary
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]["results"]), 2)

    def test_highlighting(self):
        """Test highlighting of search terms."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.highlight_options,
        )
        
        result = formatter.format_response(self.mock_response, self.mock_query)
        
        # Check that highlighting was applied
        results = result["data"]["results"]
        
        # First result should have highlighting in title
        self.assertIn("highlighted_title", results[0])
        self.assertIn("<mark>search</mark>", results[0]["highlighted_title"])
        self.assertIn("highlights", results[0])
        
        # Second result should have highlighting in title
        self.assertIn("highlighted_title", results[1])
        self.assertIn("<mark>Search</mark>", results[1]["highlighted_title"])
        self.assertIn("highlights", results[1])

    def test_extract_highlight_terms(self):
        """Test extraction of terms for highlighting."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.highlight_options,
        )
        
        # Test with simple query
        terms = formatter._extract_highlight_terms("search functionality")
        self.assertIn("search", terms)
        self.assertIn("functionality", terms)
        
        # Test with operators
        terms = formatter._extract_highlight_terms("search AND functionality OR implementation")
        self.assertIn("search", terms)
        self.assertIn("functionality", terms)
        self.assertIn("implementation", terms)
        
        # Test with quotes
        terms = formatter._extract_highlight_terms('"search functionality" implementation')
        self.assertIn("search", terms)
        self.assertIn("functionality", terms)
        self.assertIn("implementation", terms)
        
        # Test with short terms (should be filtered out)
        terms = formatter._extract_highlight_terms("search a to")
        self.assertIn("search", terms)
        self.assertNotIn("a", terms)
        self.assertNotIn("to", terms)

    def test_highlight_text(self):
        """Test highlighting of text."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.highlight_options,
        )
        
        text = "We need to implement search functionality with multiple resource types."
        terms = ["search", "functionality"]
        tag_open = "<mark>"
        tag_close = "</mark>"
        max_fragments = 2
        fragment_size = 20
        
        highlighted, fragments = formatter._highlight_text(
            text, terms, tag_open, tag_close, max_fragments, fragment_size
        )
        
        # Check that terms are highlighted
        self.assertIn("<mark>search</mark>", highlighted)
        self.assertIn("<mark>functionality</mark>", highlighted)
        
        # Check that fragments were created
        self.assertEqual(len(fragments), 2)
        
        # Check that fragments contain the highlighted terms
        for fragment in fragments:
            self.assertTrue(
                "search" in fragment or "functionality" in fragment
            )
            self.assertTrue(fragment.startswith("...") or not text.startswith(fragment.replace("...", "")))
            self.assertTrue(fragment.endswith("...") or text.endswith(fragment.replace("...", "")))

    def test_grouping(self):
        """Test grouping of results."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.grouping_options,
        )
        
        result = formatter.format_response(self.mock_response, self.mock_query)
        
        # Check that grouping was applied
        self.assertIn("groupedResults", result["data"])
        self.assertIn("groupField", result["data"])
        self.assertEqual(result["data"]["groupField"], "type")
        
        grouped = result["data"]["groupedResults"]
        self.assertIn("issue", grouped)
        self.assertIn("project", grouped)
        self.assertEqual(len(grouped["issue"]), 1)
        self.assertEqual(len(grouped["project"]), 1)

    def test_summarization(self):
        """Test summarization of descriptions."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.summarization_options,
        )
        
        result = formatter.format_response(self.mock_response, self.mock_query)
        
        # Check that summarization was applied
        results = result["data"]["results"]
        
        for r in results:
            self.assertIn("summary", r)
            self.assertTrue(len(r["summary"]) <= self.summarization_options.summarization.max_length + 3)  # +3 for "..."
            
            # If original is longer than max_length, summary should end with "..."
            if len(r["description"]) > self.summarization_options.summarization.max_length:
                self.assertTrue(r["summary"].endswith("..."))
    
    def test_format_dates(self):
        """Test formatting of dates."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=FormattingOptions(format_dates=True),
        )
        
        result = formatter.format_response(self.mock_response, self.mock_query)
        
        # Check that date formatting was applied
        results = result["data"]["results"]
        
        for r in results:
            if "createdAt" in r:
                self.assertIn("createdAtFormatted", r)
            
            if "updatedAt" in r:
                self.assertIn("updatedAtFormatted", r)
            
            if "startDate" in r:
                self.assertIn("startDateFormatted", r)
            
            if "targetDate" in r:
                self.assertIn("targetDateFormatted", r)
    
    def test_sanitize_html(self):
        """Test sanitization of HTML content."""
        # Create a formatter with HTML sanitization enabled
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=FormattingOptions(sanitize_html=True),
        )
        
        # Modify the mock response to include HTML content
        self.base_formatter.format_response.return_value.data["results"][0]["description"] = (
            "<div>We need to <strong>implement</strong> search functionality with "
            "<script>alert('xss')</script> multiple resource types.</div>"
        )
        
        result = formatter.format_response(self.mock_response, self.mock_query)
        
        # Check that HTML was sanitized
        sanitized_description = result["data"]["results"][0]["description"]
        
        # Should not contain HTML tags
        self.assertNotIn("<div>", sanitized_description)
        self.assertNotIn("<strong>", sanitized_description)
        self.assertNotIn("</strong>", sanitized_description)
        self.assertNotIn("<script>", sanitized_description)
        self.assertNotIn("</script>", sanitized_description)
        
        # Should contain the text content
        self.assertIn("We need to implement search functionality with", sanitized_description)
        self.assertIn("multiple resource types", sanitized_description)
"""
Tests for the advanced search result formatter.
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


class TestAdvancedFormatter(unittest.TestCase):
    """Tests for the advanced search result formatter."""

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

    def test_highlighting_functionality(self):
        """Test that highlighting works correctly."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.highlight_options,
        )
        
        # Test highlighting with specific text
        result = {
            "title": "Search Implementation Plan",
            "description": "We need to implement a good search functionality.",
        }
        
        highlighted = formatter._apply_highlighting(result, "implement search")
        
        # Check title highlighting
        self.assertIn("highlighted_title", highlighted)
        self.assertIn("<mark>Search</mark>", highlighted["highlighted_title"])
        
        # Check description highlighting
        self.assertIn("highlighted_description", highlighted)
        self.assertIn("<mark>implement</mark>", highlighted["highlighted_description"])
        self.assertIn("<mark>search</mark>", highlighted["highlighted_description"])
        
        # Check fragments
        self.assertIn("highlights", highlighted)
        self.assertTrue(len(highlighted["highlights"]) > 0)

    def test_highlight_text_function(self):
        """Test the highlight text function directly."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.highlight_options,
        )
        
        text = "This is a test text with search functionality to implement."
        terms = ["search", "implement"]
        
        highlighted, fragments = formatter._highlight_text(
            text, terms, "<mark>", "</mark>", 2, 20
        )
        
        # Check that both terms are highlighted
        self.assertIn("<mark>search</mark>", highlighted)
        self.assertIn("<mark>implement</mark>", highlighted)
        
        # Check fragment extraction
        self.assertEqual(len(fragments), 2)
        self.assertTrue(any("search" in f for f in fragments))
        self.assertTrue(any("implement" in f for f in fragments))

    def test_term_extraction(self):
        """Test extraction of terms from query."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.highlight_options,
        )
        
        # Test with simple terms
        terms = formatter._extract_highlight_terms("search implement test")
        self.assertIn("search", terms)
        self.assertIn("implement", terms)
        self.assertIn("test", terms)
        
        # Test with operators
        terms = formatter._extract_highlight_terms("search AND implement OR test")
        self.assertIn("search", terms)
        self.assertIn("implement", terms)
        self.assertIn("test", terms)
        
        # Test with quotes
        terms = formatter._extract_highlight_terms('"search implementation" test')
        self.assertIn("search", terms)
        self.assertIn("implementation", terms)
        self.assertIn("test", terms)
        
        # Test with short words (should be filtered out)
        terms = formatter._extract_highlight_terms("search of the test")
        self.assertIn("search", terms)
        self.assertIn("test", terms)
        self.assertNotIn("of", terms)
        self.assertNotIn("the", terms)

    def test_summarization(self):
        """Test text summarization."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.summarization_options,
        )
        
        # Test with short text (shouldn't be summarized)
        result = {"description": "Short text."}
        summarized = formatter._apply_summarization(result)
        self.assertEqual(summarized["summary"], "Short text.")
        
        # Test with long text
        result = {"description": "This is a much longer text that should be summarized correctly. It has multiple sentences with different punctuation! Does it handle questions? Yes, it should."}
        summarized = formatter._apply_summarization(result)
        self.assertTrue(len(summarized["summary"]) <= self.summarization_options.summarization.max_length + 3)  # +3 for ellipsis
        self.assertTrue(summarized["summary"].endswith("..."))
        
        # Test that it tries to break at sentence boundaries
        self.assertTrue(summarized["summary"].endswith(". ...") or 
                       summarized["summary"].endswith("! ...") or 
                       summarized["summary"].endswith("? ..."))

    def test_grouping(self):
        """Test result grouping."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=self.grouping_options,
        )
        
        # Test grouping by type
        results = [
            {"id": "1", "type": "issue"},
            {"id": "2", "type": "issue"},
            {"id": "3", "type": "project"},
            {"id": "4", "type": "user"},
        ]
        
        grouped = formatter._group_results(results, "type")
        
        self.assertEqual(len(grouped), 3)
        self.assertEqual(len(grouped["issue"]), 2)
        self.assertEqual(len(grouped["project"]), 1)
        self.assertEqual(len(grouped["user"]), 1)
        
        # Test grouping by non-existent field
        grouped = formatter._group_results(results, "nonexistent")
        self.assertEqual(len(grouped), 1)
        self.assertEqual(len(grouped["other"]), 4)

    def test_date_formatting(self):
        """Test date formatting."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=FormattingOptions(format_dates=True),
        )
        
        # Test with various date fields
        result = {
            "createdAt": "2023-01-15T14:30:25Z",
            "updatedAt": "2023-02-20T09:45:12Z",
            "startDate": "2023-03-01T00:00:00Z",
            "targetDate": "2023-04-30T00:00:00Z",
        }
        
        formatted = formatter._format_dates(result)
        
        # Check that formatted versions were added
        self.assertEqual(formatted["createdAtFormatted"], "2023-01-15 14:30")
        self.assertEqual(formatted["updatedAtFormatted"], "2023-02-20 09:45")
        self.assertEqual(formatted["startDateFormatted"], "2023-03-01")
        self.assertEqual(formatted["targetDateFormatted"], "2023-04-30")
        
        # Test with invalid date
        result = {"createdAt": "invalid-date"}
        formatted = formatter._format_dates(result)
        self.assertNotIn("createdAtFormatted", formatted)

    def test_html_sanitization(self):
        """Test HTML sanitization."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=FormattingOptions(sanitize_html=True),
        )
        
        # Test with HTML content and highlight tags
        result = {
            "description": "<p>This is <strong>bold</strong> and <script>alert('xss')</script> content.</p>",
            "highlighted_description": "This is <mark>highlighted</mark> with <div>tags</div>.",
            "summary": "<span>Summary</span> with <img src='test.jpg'>.",
        }
        
        sanitized = formatter._sanitize_html(result)
        
        # Check that HTML tags were removed but highlight tags preserved
        self.assertEqual(sanitized["description"], "This is bold and  content.")
        self.assertEqual(sanitized["highlighted_description"], "This is <mark>highlighted</mark> with tags.")
        self.assertEqual(sanitized["summary"], "Summary with .")

    def test_full_pipeline(self):
        """Test the full formatting pipeline."""
        formatter = ResultFormatter(
            base_formatter=self.base_formatter,
            options=FormattingOptions(
                highlights=HighlightOptions(enabled=True),
                summarization=SummarizationOptions(enabled=True, max_length=100),
                grouping=GroupingOptions(enabled=True),
                format_dates=True,
                sanitize_html=True,
            ),
        )
        
        result = formatter.format_response(self.mock_response, self.mock_query)
        
        # Check that base formatter was called
        self.base_formatter.format_response.assert_called_once()
        
        # Check result structure
        self.assertEqual(result["status"], "success")
        self.assertIn("groupedResults", result["data"])
        self.assertIn("groupField", result["data"])
        
        # Note: Can't check highlights, summaries, etc. in this test because
        # we're using a mock response and not executing the actual formatting logic
        # on real result content. Those are tested in the individual method tests above.
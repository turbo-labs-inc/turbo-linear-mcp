"""
Search functionality for Linear resources.

This package provides search functionality for Linear resources,
including query building, search execution, and result formatting.
"""

from src.search.engine import SearchEngine, SearchResult, SearchResponse
from src.search.formatter import SearchResultFormatter
from src.search.query import (
    QueryBuilder,
    ResourceType,
    SearchQuery,
    SearchCondition,
    SortDirection,
    SortField,
    FilterOperator,
)
from src.search.result_formatter import ResultFormatter, FormattingOptions

__all__ = [
    "SearchEngine",
    "SearchResult",
    "SearchResponse",
    "SearchResultFormatter",
    "QueryBuilder",
    "ResourceType",
    "SearchQuery",
    "SearchCondition",
    "SortDirection",
    "SortField",
    "FilterOperator",
    "ResultFormatter",
    "FormattingOptions",
]
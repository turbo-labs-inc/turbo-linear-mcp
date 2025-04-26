"""
Search functionality for Linear resources.

This package provides search functionality for Linear resources,
including query building, search execution, and result formatting.
"""

from src.search.cache import CacheOptions, SearchCache
from src.search.engine import SearchEngine, SearchResult, SearchResponse, SearchOptions
from src.search.formatter import SearchResultFormatter
from src.search.optimizer import SearchOptimizer, OptimizerConfig, RelevanceConfig
from src.search.query import (
    QueryBuilder,
    ResourceType,
    SearchQuery,
    SearchCondition,
    SortDirection,
    SortField,
    FilterOperator,
)
from src.search.result_formatter import (
    ResultFormatter,
    FormattingOptions,
    HighlightOptions,
    GroupingOptions,
    SummarizationOptions,
)

__all__ = [
    "SearchEngine",
    "SearchResult",
    "SearchResponse",
    "SearchOptions",
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
    "HighlightOptions",
    "GroupingOptions",
    "SummarizationOptions",
    "CacheOptions",
    "SearchCache",
    "SearchOptimizer",
    "OptimizerConfig",
    "RelevanceConfig",
]
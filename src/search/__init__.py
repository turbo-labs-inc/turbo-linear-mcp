"""
Search functionality for Linear resources.

This package provides search functionality for Linear resources,
including query building, search execution, and result formatting.
"""

from src.search.cache import CacheOptions, SearchCache
from src.search.engine import SearchEngine, SearchResult, SearchResponse, SearchOptions
from src.search.filter import (
    ConditionNode,
    FilterBuilder,
    FilterGroup,
    LogicalNode,
    LogicalOperator,
)
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
from src.search.response_optimization import (
    OptimizationConfig,
    PerformanceMetrics,
    ProgressiveLoadingState,
    ResponseOptimizer,
)
from src.search.result_formatter import (
    ResultFormatter,
    FormattingOptions,
    HighlightOptions,
    GroupingOptions,
    SummarizationOptions,
)
from src.search.unified import UnifiedSearch, UnifiedSearchRequest, UnifiedSearchResponse
from src.search.validation import QueryValidator, ValidationRule, ResourceTypeRules

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
    "UnifiedSearch",
    "UnifiedSearchRequest",
    "UnifiedSearchResponse",
    "QueryValidator",
    "ValidationRule",
    "ResourceTypeRules",
    "FilterGroup",
    "LogicalNode",
    "ConditionNode",
    "LogicalOperator",
    "FilterBuilder",
    "ResponseOptimizer",
    "OptimizationConfig",
    "PerformanceMetrics",
    "ProgressiveLoadingState",
]
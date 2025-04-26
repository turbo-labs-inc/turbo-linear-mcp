"""
Result formatter for search results.

This module provides advanced formatting functionality for search results,
including highlighting, summarization, and grouping.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from src.search.engine import SearchResult, SearchResponse
from src.search.formatter import SearchResultFormatter
from src.search.query import ResourceType, SearchQuery
from src.utils.logging import get_logger

logger = get_logger(__name__)


class HighlightOptions(BaseModel):
    """Options for highlighting search results."""
    
    enabled: bool = True
    tag_open: str = "<mark>"
    tag_close: str = "</mark>"
    max_fragments: int = 3
    fragment_size: int = 100


class GroupingOptions(BaseModel):
    """Options for grouping search results."""
    
    enabled: bool = False
    field: str = "type"  # Field to group by


class SummarizationOptions(BaseModel):
    """Options for summarizing search results."""
    
    enabled: bool = False
    max_length: int = 150  # Max length of summaries


class FormattingOptions(BaseModel):
    """Options for formatting search results."""
    
    highlights: HighlightOptions = Field(default_factory=HighlightOptions)
    grouping: GroupingOptions = Field(default_factory=GroupingOptions)
    summarization: SummarizationOptions = Field(default_factory=SummarizationOptions)
    include_match_context: bool = False
    format_dates: bool = True
    sanitize_html: bool = True


class ResultFormatter:
    """
    Advanced formatter for search results.
    
    This formatter extends the basic SearchResultFormatter with additional
    capabilities like text highlighting, result grouping, and summarization.
    """
    
    def __init__(
        self,
        base_formatter: Optional[SearchResultFormatter] = None,
        options: Optional[FormattingOptions] = None,
    ):
        """
        Initialize the formatter.
        
        Args:
            base_formatter: Base formatter to use for initial formatting
            options: Formatting options
        """
        self.base_formatter = base_formatter or SearchResultFormatter()
        self.options = options or FormattingOptions()
        logger.info("Result formatter initialized with options: %s", self.options)
    
    def format_response(self, response: SearchResponse, query: Optional[SearchQuery] = None) -> Dict[str, Any]:
        """
        Format a search response with advanced formatting options.
        
        Args:
            response: Search response to format
            query: Original search query for highlighting (optional)
            
        Returns:
            Formatted response with applied formatting options
        """
        # Get base formatted response
        base_response = self.base_formatter.format_response(response)
        
        # Process results with advanced formatting
        results = base_response.data["results"]
        query_text = query.text if query else None
        
        # Apply highlighting if enabled and query text is available
        if self.options.highlights.enabled and query_text:
            results = [self._apply_highlighting(result, query_text) for result in results]
        
        # Apply summarization if enabled
        if self.options.summarization.enabled:
            results = [self._apply_summarization(result) for result in results]
        
        # Apply grouping if enabled
        if self.options.grouping.enabled:
            grouped_results = self._group_results(results, self.options.grouping.field)
            base_response.data["groupedResults"] = grouped_results
            base_response.data["groupField"] = self.options.grouping.field
        
        # Format dates if enabled
        if self.options.format_dates:
            results = [self._format_dates(result) for result in results]
        
        # Sanitize HTML content if enabled
        if self.options.sanitize_html:
            results = [self._sanitize_html(result) for result in results]
        
        base_response.data["results"] = results
        return base_response.dict()
    
    def _apply_highlighting(self, result: Dict[str, Any], query_text: str) -> Dict[str, Any]:
        """
        Apply text highlighting to search result.
        
        Args:
            result: Search result to highlight
            query_text: Text to highlight
            
        Returns:
            Result with highlighting
        """
        # Add a highlights field to track all highlights
        result["highlights"] = {}
        
        # Terms to highlight (split query into individual terms)
        highlight_terms = self._extract_highlight_terms(query_text)
        
        # Fields to check for highlighting
        fields_to_highlight = ["title", "description"]
        
        for field in fields_to_highlight:
            if field in result and result[field]:
                highlighted_text, fragments = self._highlight_text(
                    result[field],
                    highlight_terms,
                    self.options.highlights.tag_open,
                    self.options.highlights.tag_close,
                    self.options.highlights.max_fragments,
                    self.options.highlights.fragment_size,
                )
                
                # Only update the text if we found matches
                if highlighted_text != result[field]:
                    result[f"highlighted_{field}"] = highlighted_text
                    result["highlights"][field] = fragments
        
        return result
    
    def _extract_highlight_terms(self, query_text: str) -> List[str]:
        """
        Extract terms from query text for highlighting.
        
        Args:
            query_text: Query text
            
        Returns:
            List of terms to highlight
        """
        # Remove quotes and operators, split into terms
        cleaned_text = query_text.replace('"', '').replace('AND', ' ').replace('OR', ' ')
        terms = [term.strip() for term in cleaned_text.split() if len(term.strip()) > 2]
        
        # Remove duplicates and return
        return list(set(terms))
    
    def _highlight_text(
        self,
        text: str,
        terms: List[str],
        tag_open: str,
        tag_close: str,
        max_fragments: int,
        fragment_size: int,
    ) -> Tuple[str, List[str]]:
        """
        Highlight terms in text and extract fragments.
        
        Args:
            text: Text to highlight
            terms: Terms to highlight
            tag_open: Opening highlight tag
            tag_close: Closing highlight tag
            max_fragments: Maximum number of fragments to extract
            fragment_size: Size of fragments
            
        Returns:
            Tuple of (highlighted full text, list of fragments)
        """
        # Create copy of text for highlighting
        highlighted_text = text
        fragments = []
        
        # Find positions of all terms in text (case insensitive)
        text_lower = text.lower()
        match_positions = []
        
        for term in terms:
            term_lower = term.lower()
            start_pos = 0
            
            while start_pos < len(text_lower):
                pos = text_lower.find(term_lower, start_pos)
                if pos == -1:
                    break
                    
                match_positions.append((pos, pos + len(term)))
                start_pos = pos + 1
        
        # Sort by position
        match_positions.sort()
        
        # Process the match positions to avoid overlapping highlighting
        processed_positions = []
        for start, end in match_positions:
            # Check if this position overlaps with any previously processed position
            overlaps = False
            for p_start, p_end in processed_positions:
                if (start <= p_end and end >= p_start):
                    overlaps = True
                    break
            
            if not overlaps:
                processed_positions.append((start, end))
        
        # Apply highlighting in reverse to avoid position shifts
        for start, end in sorted(processed_positions, reverse=True):
            term = text[start:end]
            highlighted_text = highlighted_text[:start] + tag_open + term + tag_close + highlighted_text[end:]
        
        # Extract fragments for context (non-overlapping)
        if max_fragments > 0 and processed_positions:
            extracted_fragments = 0
            
            for start, end in processed_positions:
                if extracted_fragments >= max_fragments:
                    break
                
                # Calculate fragment boundaries
                fragment_start = max(0, start - fragment_size // 2)
                fragment_end = min(len(text), end + fragment_size // 2)
                
                # Extract fragment and add ellipsis if needed
                fragment = text[fragment_start:fragment_end]
                if fragment_start > 0:
                    fragment = "..." + fragment
                if fragment_end < len(text):
                    fragment += "..."
                
                fragments.append(fragment)
                extracted_fragments += 1
        
        return highlighted_text, fragments
    
    def _apply_summarization(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply summarization to search result.
        
        Args:
            result: Search result to summarize
            
        Returns:
            Result with summarization
        """
        if "description" in result and result["description"]:
            description = result["description"]
            
            # Simple summarization - truncate and add ellipsis
            if len(description) > self.options.summarization.max_length:
                # Try to break at a sentence or period
                cutoff = min(self.options.summarization.max_length, len(description))
                
                # Look for a period, question mark, or exclamation point followed by a space
                for i in range(cutoff - 5, max(0, cutoff - 40), -1):
                    if description[i] in ['.', '?', '!'] and i + 1 < len(description) and description[i + 1] == ' ':
                        cutoff = i + 1
                        break
                
                result["summary"] = description[:cutoff].strip() + "..."
            else:
                result["summary"] = description
        
        return result
    
    def _group_results(self, results: List[Dict[str, Any]], field: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group results by a field.
        
        Args:
            results: Results to group
            field: Field to group by
            
        Returns:
            Dictionary of grouped results
        """
        grouped = {}
        
        for result in results:
            # Get the group key
            if field in result:
                key = str(result[field])
            else:
                key = "other"
            
            # Initialize group if needed
            if key not in grouped:
                grouped[key] = []
            
            # Add result to group
            grouped[key].append(result)
        
        return grouped
    
    def _format_dates(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format dates in search result.
        
        Args:
            result: Search result to format dates in
            
        Returns:
            Result with formatted dates
        """
        date_fields = ["createdAt", "updatedAt", "startDate", "targetDate"]
        
        for field in date_fields:
            if field in result and result[field]:
                # Convert ISO format to human-readable format
                try:
                    # Keep ISO format but also add a human-readable version
                    iso_date = result[field]
                    
                    # Remove time portion for date-only fields
                    if field in ["startDate", "targetDate"]:
                        human_date = iso_date.split("T")[0]
                    else:
                        # Format: YYYY-MM-DD HH:MM
                        date_part, time_part = iso_date.replace("Z", "").split("T")
                        time_part = time_part.split(".")[0]  # Remove microseconds
                        time_part = time_part[:5]  # Keep only hours and minutes
                        human_date = f"{date_part} {time_part}"
                    
                    result[f"{field}Formatted"] = human_date
                except (ValueError, AttributeError, IndexError):
                    # Keep original if we can't format it
                    pass
        
        return result
    
    def _sanitize_html(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize HTML content in result.
        
        Args:
            result: Search result to sanitize
            
        Returns:
            Sanitized result
        """
        # Fields that might contain HTML
        html_fields = ["description", "highlighted_description", "summary"]
        
        for field in html_fields:
            if field in result and result[field]:
                # Very basic HTML sanitization - remove HTML tags except highlight tags
                text = result[field]
                
                # Preserve highlight tags
                highlight_open = self.options.highlights.tag_open
                highlight_close = self.options.highlights.tag_close
                
                # Replace highlight tags with placeholders
                text = text.replace(highlight_open, "___HIGHLIGHT_OPEN___")
                text = text.replace(highlight_close, "___HIGHLIGHT_CLOSE___")
                
                # Remove HTML tags with simple regex-like approach
                sanitized = ""
                in_tag = False
                for char in text:
                    if char == '<':
                        in_tag = True
                    elif char == '>':
                        in_tag = False
                    elif not in_tag:
                        sanitized += char
                
                # Restore highlight tags
                sanitized = sanitized.replace("___HIGHLIGHT_OPEN___", highlight_open)
                sanitized = sanitized.replace("___HIGHLIGHT_CLOSE___", highlight_close)
                
                result[field] = sanitized
        
        return result
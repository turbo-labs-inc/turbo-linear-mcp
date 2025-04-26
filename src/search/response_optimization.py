"""
Search response optimization.

This module provides functionality for optimizing search responses,
including compression, batching, and progressive loading.
"""

import base64
import gzip
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from src.search.engine import SearchResponse, SearchResult
from src.search.query import ResourceType, SearchQuery
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OptimizationConfig(BaseModel):
    """Configuration for response optimization."""
    
    # Content optimization options
    compress_large_responses: bool = True
    compression_threshold_bytes: int = 10 * 1024  # 10KB
    trim_fields: bool = True
    max_description_length: int = 300
    include_metadata: bool = True
    
    # Progressive loading options
    enable_progressive_loading: bool = True
    results_per_page: int = 20
    max_pages: int = 10
    
    # Batching options
    enable_batching: bool = True
    max_batch_size: int = 100
    batch_timeout_ms: int = 50
    
    # Streaming options
    enable_streaming: bool = False
    stream_chunk_size: int = 5
    
    # Performance metrics
    include_performance_metrics: bool = True


class ProgressiveLoadingState(BaseModel):
    """State for progressive loading."""
    
    total_results: int
    loaded_results: int
    current_page: int
    total_pages: int
    has_more: bool
    next_cursor: Optional[str]
    load_progress: float  # 0.0 to 1.0


class PerformanceMetrics(BaseModel):
    """Performance metrics for search response."""
    
    query_time_ms: float
    result_count: int
    total_count: int
    response_size_bytes: int
    compressed_size_bytes: Optional[int] = None
    compression_ratio: Optional[float] = None
    cache_hit: bool = False
    cache_age_seconds: Optional[float] = None
    query_complexity: int = 1  # 1-10 scale


class ResponseOptimizer:
    """
    Optimizer for search responses.
    
    This class provides techniques to optimize search responses for
    different client scenarios, including compression, progressive
    loading, and batching.
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Initialize the response optimizer.
        
        Args:
            config: Optimization configuration
        """
        self.config = config or OptimizationConfig()
        logger.info("Response optimizer initialized with config: %s", self.config)
    
    def optimize_response(
        self, 
        response: SearchResponse,
        format_type: str = "json",
        client_capabilities: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize a search response for delivery to clients.
        
        Args:
            response: Search response to optimize
            format_type: Output format type (json, compressed, streamed)
            client_capabilities: Client capabilities for adaptive optimization
            
        Returns:
            Optimized response as a dictionary
        """
        start_time = time.time()
        
        # Convert response to dictionary
        response_dict = response.dict()
        
        # Calculate initial size
        initial_json = json.dumps(response_dict)
        initial_size = len(initial_json.encode("utf-8"))
        
        # Apply optimization techniques
        optimized_dict = self._optimize_content(response_dict)
        
        # Add pagination for progressive loading if enabled
        if self.config.enable_progressive_loading:
            optimized_dict = self._add_progressive_loading(optimized_dict)
        
        # Add performance metrics if enabled
        if self.config.include_performance_metrics:
            # Calculate optimized size
            optimized_json = json.dumps(optimized_dict)
            optimized_size = len(optimized_json.encode("utf-8"))
            
            metrics = self._calculate_performance_metrics(
                response=response,
                initial_size=initial_size,
                optimized_size=optimized_size,
                query_time=response.execution_time or 0,
                optimization_time=time.time() - start_time,
            )
            
            optimized_dict["performance_metrics"] = metrics.dict()
        
        # Apply format-specific optimizations
        if format_type == "compressed" and self.config.compress_large_responses:
            optimized_dict = self._compress_response(optimized_dict)
        
        logger.info(
            "Optimized search response: initial size=%d bytes, optimized size=%d bytes",
            initial_size,
            len(json.dumps(optimized_dict).encode("utf-8")),
        )
        
        return optimized_dict
    
    def _optimize_content(self, response_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize response content.
        
        Args:
            response_dict: Response dictionary to optimize
            
        Returns:
            Optimized response dictionary
        """
        # Create a copy to avoid modifying the original
        optimized = response_dict.copy()
        
        # Optimize results
        if "results" in optimized:
            optimized_results = []
            
            for result in optimized["results"]:
                # Trim description if enabled and too long
                if (self.config.trim_fields and 
                    "description" in result and 
                    result["description"] and 
                    len(result["description"]) > self.config.max_description_length):
                    # Try to trim at a sentence boundary
                    description = result["description"]
                    cutoff = min(self.config.max_description_length, len(description))
                    
                    # Look for a period, question mark, or exclamation point
                    for i in range(cutoff - 5, max(0, cutoff - 50), -1):
                        if description[i] in ['.', '?', '!'] and i + 1 < len(description) and description[i + 1] == ' ':
                            cutoff = i + 1
                            break
                    
                    result["description"] = description[:cutoff].strip()
                    result["description_truncated"] = True
                
                # Remove metadata if not needed
                if not self.config.include_metadata:
                    result.pop("additional_data", None)
                
                optimized_results.append(result)
            
            optimized["results"] = optimized_results
        
        return optimized
    
    def _add_progressive_loading(self, response_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add progressive loading information to response.
        
        Args:
            response_dict: Response dictionary
            
        Returns:
            Response dictionary with progressive loading information
        """
        # Create a copy to avoid modifying the original
        optimized = response_dict.copy()
        
        # Calculate pagination
        total_results = len(optimized.get("results", []))
        total_count = optimized.get("total_count", total_results)
        results_per_page = self.config.results_per_page
        
        # Calculate total pages
        total_pages = (total_count + results_per_page - 1) // results_per_page
        total_pages = min(total_pages, self.config.max_pages)
        
        # Slice results for first page if there are a lot
        if total_results > results_per_page:
            optimized["results"] = optimized["results"][:results_per_page]
            optimized["results_paged"] = True
        
        # Add progressive loading state
        loading_state = ProgressiveLoadingState(
            total_results=total_count,
            loaded_results=min(results_per_page, total_results),
            current_page=1,
            total_pages=total_pages,
            has_more=total_results > results_per_page,
            next_cursor=optimized.get("cursor"),
            load_progress=min(results_per_page, total_results) / max(1, total_count),
        )
        
        optimized["loading_state"] = loading_state.dict()
        
        return optimized
    
    def _compress_response(self, response_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress a response dictionary.
        
        Args:
            response_dict: Response dictionary to compress
            
        Returns:
            Compressed response dictionary
        """
        # Convert to JSON string
        json_data = json.dumps(response_dict)
        json_bytes = json_data.encode("utf-8")
        
        # Only compress if above threshold
        if len(json_bytes) <= self.config.compression_threshold_bytes:
            return response_dict
        
        # Compress the data
        compressed_bytes = gzip.compress(json_bytes)
        
        # Encode as base64 for safe transport
        compressed_base64 = base64.b64encode(compressed_bytes).decode("ascii")
        
        # Return a wrapper with the compressed data
        return {
            "compressed": True,
            "original_size": len(json_bytes),
            "compressed_size": len(compressed_bytes),
            "compression_ratio": len(compressed_bytes) / len(json_bytes),
            "data": compressed_base64,
            "format": "gzip+base64",
        }
    
    def decompress_response(self, compressed_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decompress a compressed response.
        
        Args:
            compressed_response: Compressed response dictionary
            
        Returns:
            Decompressed response dictionary
        """
        if not compressed_response.get("compressed", False):
            return compressed_response
        
        # Get the compressed data
        compressed_base64 = compressed_response["data"]
        
        # Decode base64
        compressed_bytes = base64.b64decode(compressed_base64)
        
        # Decompress
        json_bytes = gzip.decompress(compressed_bytes)
        
        # Parse JSON
        return json.loads(json_bytes.decode("utf-8"))
    
    def _calculate_performance_metrics(
        self,
        response: SearchResponse,
        initial_size: int,
        optimized_size: int,
        query_time: float,
        optimization_time: float,
    ) -> PerformanceMetrics:
        """
        Calculate performance metrics for the response.
        
        Args:
            response: Search response
            initial_size: Initial size in bytes
            optimized_size: Optimized size in bytes
            query_time: Query execution time in seconds
            optimization_time: Optimization time in seconds
            
        Returns:
            Performance metrics
        """
        # Calculate query complexity
        complexity = 1
        if response.query:
            # Add complexity based on resource types
            complexity += min(2, len(response.query.resource_types))
            
            # Add complexity based on conditions
            complexity += min(3, len(response.query.conditions))
            
            # Add complexity for sort operations
            if response.query.sort:
                complexity += 1
            
            # Add complexity for search text
            if response.query.text and len(response.query.text) > 10:
                complexity += 1
        
        # Cap complexity at 10
        complexity = min(10, complexity)
        
        # Calculate compression metrics if we'll compress
        compressed_size = None
        compression_ratio = None
        
        if initial_size > self.config.compression_threshold_bytes and self.config.compress_large_responses:
            # Create a compressed version to measure
            json_bytes = json.dumps(response.dict()).encode("utf-8")
            compressed_bytes = gzip.compress(json_bytes)
            compressed_size = len(compressed_bytes)
            compression_ratio = compressed_size / initial_size
        
        return PerformanceMetrics(
            query_time_ms=query_time * 1000,  # Convert to milliseconds
            result_count=len(response.results),
            total_count=response.total_count,
            response_size_bytes=initial_size,
            compressed_size_bytes=compressed_size,
            compression_ratio=compression_ratio,
            cache_hit=response.cache_hit if hasattr(response, "cache_hit") else False,
            query_complexity=complexity,
        )
    
    def create_batched_responses(self, response: SearchResponse) -> List[Dict[str, Any]]:
        """
        Split a large response into smaller batches for efficient delivery.
        
        Args:
            response: Search response to batch
            
        Returns:
            List of batched response dictionaries
        """
        if not self.config.enable_batching:
            return [response.dict()]
        
        # Convert to dictionary
        response_dict = response.dict()
        
        # Get all results
        all_results = response_dict.get("results", [])
        
        # If results are small enough, return as is
        if len(all_results) <= self.config.max_batch_size:
            return [response_dict]
        
        # Calculate number of batches
        batch_size = self.config.max_batch_size
        num_batches = (len(all_results) + batch_size - 1) // batch_size
        
        # Create batches
        batches = []
        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, len(all_results))
            
            # Create a copy of the response with just this batch of results
            batch = response_dict.copy()
            batch["results"] = all_results[start_idx:end_idx]
            batch["batch_index"] = i
            batch["total_batches"] = num_batches
            batch["batch_size"] = end_idx - start_idx
            
            # Update has_more flag to reflect if this batch has more results
            batch["has_more"] = i < num_batches - 1 or response_dict.get("has_more", False)
            
            batches.append(batch)
        
        return batches
    
    def create_streamed_responses(self, response: SearchResponse) -> List[Dict[str, Any]]:
        """
        Create a series of responses for streaming.
        
        Args:
            response: Search response to stream
            
        Returns:
            List of response chunks for streaming
        """
        if not self.config.enable_streaming:
            return [response.dict()]
        
        # Convert to dictionary
        response_dict = response.dict()
        
        # Get all results
        all_results = response_dict.get("results", [])
        
        # Calculate number of chunks
        chunk_size = self.config.stream_chunk_size
        num_chunks = (len(all_results) + chunk_size - 1) // chunk_size
        
        # Create chunks
        chunks = []
        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(all_results))
            
            # Create chunk with just a subset of results
            chunk = {
                "chunk_index": i,
                "total_chunks": num_chunks,
                "results": all_results[start_idx:end_idx],
                "has_more": i < num_chunks - 1,
                "total_count": response_dict.get("total_count", len(all_results)),
            }
            
            chunks.append(chunk)
        
        return chunks
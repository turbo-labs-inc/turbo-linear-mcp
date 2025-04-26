"""
Batch processing for feature lists.

This module provides functionality for batch processing of feature lists.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from src.features.formatter import ConversionResponse, FeatureListFormatter
from src.features.parser import FeatureFormat, FeatureList, FeatureParser
from src.features.processor import FeatureListProcessor, ProcessingResult, ProcessorOptions
from src.features.validation import FeatureListValidator, ValidationResult
from src.linear.client import LinearClient
from src.utils.errors import ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BatchItem(BaseModel):
    """Model for a batch processing item."""

    text: str
    format: Optional[FeatureFormat] = None
    team_id: Optional[str] = None
    team_key: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    options: Optional[ProcessorOptions] = None


class BatchResult(BaseModel):
    """Model for a batch processing result."""

    success: bool
    validation: Optional[ValidationResult] = None
    result: Optional[ConversionResponse] = None
    error: Optional[str] = None


class BatchRequest(BaseModel):
    """Model for a batch processing request."""

    items: List[BatchItem]
    validate_only: bool = False
    global_options: Optional[ProcessorOptions] = None


class BatchResponse(BaseModel):
    """Model for a batch processing response."""

    results: List[BatchResult]
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    validation_count: int = 0


class BatchProcessor:
    """
    Batch processor for feature lists.
    
    This class provides functionality for batch processing of feature lists.
    """

    def __init__(
        self,
        linear_client: LinearClient,
        validator: Optional[FeatureListValidator] = None,
        formatter: Optional[FeatureListFormatter] = None,
    ):
        """
        Initialize the batch processor.
        
        Args:
            linear_client: Linear API client
            validator: Feature list validator
            formatter: Feature list formatter
        """
        self.linear_client = linear_client
        self.validator = validator or FeatureListValidator()
        self.formatter = formatter or FeatureListFormatter()
        logger.info("Batch processor initialized")

    async def process_batch(self, request: BatchRequest) -> BatchResponse:
        """
        Process a batch of feature lists.
        
        Args:
            request: Batch request
            
        Returns:
            Batch response
        """
        results = []
        
        # Process each item
        for item in request.items:
            try:
                # Apply global options if not overridden
                options = item.options or request.global_options or ProcessorOptions()
                
                # Override specific options
                if item.team_id:
                    options.team_id = item.team_id
                if item.team_key:
                    options.team_key = item.team_key
                if item.project_id:
                    options.project_id = item.project_id
                if item.project_name:
                    options.project_name = item.project_name
                
                # Validate feature list
                validation = self.validator.validate_text(item.text, item.format)
                
                if not validation.valid:
                    results.append(
                        BatchResult(
                            success=False,
                            validation=validation,
                            error="Feature list validation failed",
                        )
                    )
                    continue
                
                # If validate_only, don't process
                if request.validate_only:
                    results.append(
                        BatchResult(
                            success=True,
                            validation=validation,
                        )
                    )
                    continue
                
                # Process feature list
                processor = FeatureListProcessor(self.linear_client, options)
                process_result = await processor.process_text(item.text, item.format)
                
                # Format result
                conversion_response = self.formatter.format_result(process_result)
                
                results.append(
                    BatchResult(
                        success=True,
                        validation=validation,
                        result=conversion_response,
                    )
                )
            
            except Exception as e:
                logger.error(f"Error processing batch item: {e}")
                results.append(
                    BatchResult(
                        success=False,
                        error=str(e),
                    )
                )
        
        # Compile overall counts
        total_count = len(results)
        success_count = sum(1 for result in results if result.success)
        failure_count = total_count - success_count
        validation_count = sum(1 for result in results if result.validation is not None)
        
        return BatchResponse(
            results=results,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            validation_count=validation_count,
        )

    async def process_concurrent(
        self, request: BatchRequest, concurrency: int = 5
    ) -> BatchResponse:
        """
        Process a batch of feature lists concurrently.
        
        Args:
            request: Batch request
            concurrency: Maximum number of concurrent processes
            
        Returns:
            Batch response
        """
        results = [None] * len(request.items)
        
        async def process_item(index: int, item: BatchItem) -> None:
            try:
                # Apply global options if not overridden
                options = item.options or request.global_options or ProcessorOptions()
                
                # Override specific options
                if item.team_id:
                    options.team_id = item.team_id
                if item.team_key:
                    options.team_key = item.team_key
                if item.project_id:
                    options.project_id = item.project_id
                if item.project_name:
                    options.project_name = item.project_name
                
                # Validate feature list
                validation = self.validator.validate_text(item.text, item.format)
                
                if not validation.valid:
                    results[index] = BatchResult(
                        success=False,
                        validation=validation,
                        error="Feature list validation failed",
                    )
                    return
                
                # If validate_only, don't process
                if request.validate_only:
                    results[index] = BatchResult(
                        success=True,
                        validation=validation,
                    )
                    return
                
                # Process feature list
                processor = FeatureListProcessor(self.linear_client, options)
                process_result = await processor.process_text(item.text, item.format)
                
                # Format result
                conversion_response = self.formatter.format_result(process_result)
                
                results[index] = BatchResult(
                    success=True,
                    validation=validation,
                    result=conversion_response,
                )
            
            except Exception as e:
                logger.error(f"Error processing batch item {index}: {e}")
                results[index] = BatchResult(
                    success=False,
                    error=str(e),
                )
        
        # Use a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_process_item(index: int, item: BatchItem) -> None:
            async with semaphore:
                await process_item(index, item)
        
        # Process items concurrently
        tasks = [
            bounded_process_item(i, item)
            for i, item in enumerate(request.items)
        ]
        
        await asyncio.gather(*tasks)
        
        # Compile overall counts
        total_count = len(results)
        success_count = sum(1 for result in results if result.success)
        failure_count = total_count - success_count
        validation_count = sum(1 for result in results if result.validation is not None)
        
        return BatchResponse(
            results=results,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            validation_count=validation_count,
        )
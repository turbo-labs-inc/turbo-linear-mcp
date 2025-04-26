"""
Error handling utilities for the Linear MCP Server.

This module provides exception classes and handlers for consistent error responses.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ErrorCode(str, Enum):
    """Enumeration of error codes for consistent error responses."""

    # Server errors (1xxx)
    SERVER_ERROR = "1000"
    NOT_IMPLEMENTED = "1001"
    SERVICE_UNAVAILABLE = "1002"
    TIMEOUT = "1003"
    RATE_LIMITED = "1004"
    
    # Authentication errors (2xxx)
    UNAUTHORIZED = "2000"
    INVALID_API_KEY = "2001"
    EXPIRED_TOKEN = "2002"
    INSUFFICIENT_PERMISSIONS = "2003"
    
    # Request errors (3xxx)
    BAD_REQUEST = "3000"
    VALIDATION_ERROR = "3001"
    NOT_FOUND = "3002"
    METHOD_NOT_ALLOWED = "3003"
    CONFLICT = "3004"
    
    # Linear API errors (4xxx)
    LINEAR_API_ERROR = "4000"
    LINEAR_RATE_LIMITED = "4001"
    LINEAR_UNAUTHORIZED = "4002"
    LINEAR_NOT_FOUND = "4003"
    
    # Feature list errors (5xxx)
    FEATURE_LIST_PARSE_ERROR = "5000"
    FEATURE_LIST_VALIDATION_ERROR = "5001"
    FEATURE_LIST_CREATION_ERROR = "5002"
    
    # Search errors (6xxx)
    SEARCH_PARSE_ERROR = "6000"
    SEARCH_EXECUTION_ERROR = "6001"
    SEARCH_TIMEOUT = "6002"
    
    # MCP protocol errors (7xxx)
    MCP_PROTOCOL_ERROR = "7000"
    MCP_VERSION_MISMATCH = "7001"
    MCP_UNSUPPORTED_CAPABILITY = "7002"


class ErrorDetail(BaseModel):
    """Model representing detailed error information."""

    location: Optional[str] = None
    param: Optional[str] = None
    value: Optional[Any] = None
    message: str


class ErrorResponse(BaseModel):
    """Model representing a standardized error response."""

    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None


class MCPError(Exception):
    """Base exception class for MCP server errors."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[List[ErrorDetail]] = None,
    ):
        """
        Initialize a new MCP error.
        
        Args:
            code: Error code
            message: Error message
            status_code: HTTP status code to return
            details: Optional list of error details
        """
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(self.message)


class ValidationError(MCPError):
    """Exception for validation errors."""

    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[List[ErrorDetail]] = None,
    ):
        """Initialize a new validation error."""
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class NotFoundError(MCPError):
    """Exception for resource not found errors."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[List[ErrorDetail]] = None,
    ):
        """Initialize a new not found error."""
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class UnauthorizedError(MCPError):
    """Exception for authentication errors."""

    def __init__(
        self,
        message: str = "Unauthorized",
        details: Optional[List[ErrorDetail]] = None,
    ):
        """Initialize a new unauthorized error."""
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class LinearAPIError(MCPError):
    """Exception for Linear API errors."""

    def __init__(
        self,
        message: str = "Linear API error",
        details: Optional[List[ErrorDetail]] = None,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
    ):
        """Initialize a new Linear API error."""
        super().__init__(
            code=ErrorCode.LINEAR_API_ERROR,
            message=message,
            status_code=status_code,
            details=details,
        )


def setup_error_handlers(app: FastAPI) -> None:
    """
    Configure error handlers for FastAPI application.
    
    Args:
        app: FastAPI application
    """
    
    @app.exception_handler(MCPError)
    async def mcp_error_handler(request: Request, exc: MCPError) -> JSONResponse:
        """Handle MCP errors and return standardized error responses."""
        logger.error(
            f"MCP error: {exc.code} - {exc.message}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "status_code": exc.status_code,
                "error_code": exc.code,
                "error_details": [detail.dict() for detail in (exc.details or [])],
            },
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, "request_id", None),
            ).dict(),
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle FastAPI request validation errors."""
        details = []
        for error in exc.errors():
            location = ".".join(str(loc) for loc in error.get("loc", []))
            details.append(
                ErrorDetail(
                    location=location,
                    message=error.get("msg", "Validation error"),
                    param=error.get("loc", [""])[-1] if error.get("loc") else None,
                )
            )
        
        logger.error(
            "Request validation error",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "validation_errors": exc.errors(),
            },
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                code=ErrorCode.VALIDATION_ERROR,
                message="Request validation error",
                details=details,
                request_id=getattr(request.state, "request_id", None),
            ).dict(),
        )
    
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions and return standardized error responses."""
        logger.exception(
            f"Unhandled exception: {str(exc)}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "exception_type": type(exc).__name__,
            },
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                code=ErrorCode.SERVER_ERROR,
                message="An unexpected error occurred",
                request_id=getattr(request.state, "request_id", None),
            ).dict(),
        )
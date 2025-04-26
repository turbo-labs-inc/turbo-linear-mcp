"""
Tests for the error handling utilities.
"""

import pytest
from fastapi import FastAPI, Request, status
from fastapi.testclient import TestClient

from src.utils.errors import (
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    LinearAPIError,
    MCPError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    setup_error_handlers,
)


def test_error_response_model():
    """Test the error response model."""
    error = ErrorResponse(
        code=ErrorCode.SERVER_ERROR,
        message="Test error",
        details=[
            ErrorDetail(
                location="body",
                param="field",
                value="invalid",
                message="Invalid value",
            )
        ],
        request_id="test-request-id",
    )
    
    assert error.code == ErrorCode.SERVER_ERROR
    assert error.message == "Test error"
    assert len(error.details) == 1
    assert error.details[0].location == "body"
    assert error.details[0].param == "field"
    assert error.details[0].value == "invalid"
    assert error.details[0].message == "Invalid value"
    assert error.request_id == "test-request-id"


def test_mcp_error():
    """Test the base MCP error class."""
    error = MCPError(
        code=ErrorCode.SERVER_ERROR,
        message="Test error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=[
            ErrorDetail(
                location="body",
                param="field",
                value="invalid",
                message="Invalid value",
            )
        ],
    )
    
    assert error.code == ErrorCode.SERVER_ERROR
    assert error.message == "Test error"
    assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert len(error.details) == 1
    assert error.details[0].location == "body"
    assert error.details[0].param == "field"
    assert error.details[0].value == "invalid"
    assert error.details[0].message == "Invalid value"


def test_specific_error_classes():
    """Test specific error classes."""
    errors = [
        (ValidationError(), ErrorCode.VALIDATION_ERROR, status.HTTP_400_BAD_REQUEST),
        (NotFoundError(), ErrorCode.NOT_FOUND, status.HTTP_404_NOT_FOUND),
        (UnauthorizedError(), ErrorCode.UNAUTHORIZED, status.HTTP_401_UNAUTHORIZED),
        (LinearAPIError(), ErrorCode.LINEAR_API_ERROR, status.HTTP_502_BAD_GATEWAY),
    ]
    
    for error, expected_code, expected_status in errors:
        assert error.code == expected_code
        assert error.status_code == expected_status


def test_error_handlers():
    """Test that error handlers correctly format error responses."""
    app = FastAPI()
    setup_error_handlers(app)
    
    @app.get("/test-validation-error")
    async def test_validation_error():
        raise ValidationError("Validation failed")
    
    @app.get("/test-not-found")
    async def test_not_found():
        raise NotFoundError("Resource not found")
    
    @app.get("/test-unauthorized")
    async def test_unauthorized():
        raise UnauthorizedError("Authentication required")
    
    @app.get("/test-linear-api-error")
    async def test_linear_api_error():
        raise LinearAPIError("Linear API error occurred")
    
    @app.get("/test-unhandled-error")
    async def test_unhandled_error():
        raise RuntimeError("Unhandled error")
    
    client = TestClient(app)
    
    # Test validation error
    response = client.get("/test-validation-error")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["code"] == ErrorCode.VALIDATION_ERROR
    assert data["message"] == "Validation failed"
    
    # Test not found error
    response = client.get("/test-not-found")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["code"] == ErrorCode.NOT_FOUND
    assert data["message"] == "Resource not found"
    
    # Test unauthorized error
    response = client.get("/test-unauthorized")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["code"] == ErrorCode.UNAUTHORIZED
    assert data["message"] == "Authentication required"
    
    # Test Linear API error
    response = client.get("/test-linear-api-error")
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    data = response.json()
    assert data["code"] == ErrorCode.LINEAR_API_ERROR
    assert data["message"] == "Linear API error occurred"
    
    # Test unhandled error
    response = client.get("/test-unhandled-error")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert data["code"] == ErrorCode.SERVER_ERROR
    assert data["message"] == "An unexpected error occurred"
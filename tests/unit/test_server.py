"""
Tests for the server module.
"""

import asyncio
from typing import Dict

import pytest
from fastapi.testclient import TestClient

from src.server.server import create_server


def test_create_server(test_config):
    """Test creating a server instance."""
    server = create_server(test_config)
    assert server is not None
    assert server.config == test_config


def test_server_health_endpoint(test_config):
    """Test the health check endpoint."""
    server = create_server(test_config)
    client = TestClient(server.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_server_root_endpoint(test_config):
    """Test the root endpoint."""
    server = create_server(test_config)
    client = TestClient(server.app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["server"] == "Linear MCP Server"
    assert data["version"] == "0.1.0"
    assert data["status"] == "running"


def test_server_status_endpoint(test_config):
    """Test the status endpoint."""
    server = create_server(test_config)
    client = TestClient(server.app)
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["version"] == "0.1.0"
    assert isinstance(data["uptime"], float)
    assert isinstance(data["connections"], int)
    assert data["environment"] == "test"


def test_server_cors_middleware(test_config):
    """Test that CORS middleware is properly configured."""
    server = create_server(test_config)
    client = TestClient(server.app)
    response = client.options(
        "/",
        headers={
            "Origin": "http://testserver",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Example",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"


def test_server_request_logging(test_config, caplog):
    """Test that requests are properly logged."""
    # This test verifies that the request logging middleware captures request information
    with caplog.at_level("DEBUG"):
        server = create_server(test_config)
        client = TestClient(server.app)
        client.get("/health")
        
        assert any("Request: GET /health" in message for message in caplog.messages)
        assert any("Response: 200" in message for message in caplog.messages)
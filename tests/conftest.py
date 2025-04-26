"""
Test configuration and fixtures for Linear MCP Server.

This module provides pytest fixtures and configuration for testing.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Generator

import pytest
from pydantic import BaseModel

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import Config, LinearConfig, LoggingConfig, ServerConfig


@pytest.fixture
def test_config() -> Config:
    """Provide a test configuration."""
    return Config(
        linear=LinearConfig(
            api_key="test_api_key",
            api_url="https://api.linear.app/graphql",
            timeout=5,
            max_retries=1,
            retry_delay=0,
        ),
        server=ServerConfig(
            host="127.0.0.1",
            port=8000,
            workers=1,
            reload=False,
            cors_origins=["*"],
            request_timeout=10,
        ),
        logging=LoggingConfig(
            level="DEBUG",
            config_file=None,
            log_file=None,
        ),
        debug=True,
        environment="test",
    )


@pytest.fixture
def test_env_vars(monkeypatch: pytest.MonkeyPatch) -> Generator[Dict[str, str], None, None]:
    """Set up test environment variables."""
    env_vars = {
        "LINEAR_MCP_LINEAR_API_KEY": "test_env_api_key",
        "LINEAR_MCP_SERVER_PORT": "9000",
        "LINEAR_MCP_LOGGING_LEVEL": "DEBUG",
        "LINEAR_MCP_DEBUG": "true",
        "LINEAR_MCP_ENVIRONMENT": "test",
    }
    
    # Apply environment variables
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    yield env_vars
    
    # Clean up environment variables
    for key in env_vars:
        monkeypatch.delenv(key, raising=False)
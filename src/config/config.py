"""
Configuration management for the Linear MCP Server.

This module handles loading and validating configuration from various sources
including configuration files, environment variables, and command-line arguments.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, Field


class LinearConfig(BaseModel):
    """Configuration for Linear API integration."""

    api_key: str = Field(..., description="Linear API key")
    api_url: str = Field(
        "https://api.linear.app/graphql", description="Linear API URL"
    )
    timeout: int = Field(30, description="API request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of API request retries")
    retry_delay: int = Field(1, description="Delay between retries in seconds")


class ServerConfig(BaseModel):
    """Configuration for the MCP server."""

    host: str = Field("127.0.0.1", description="Server host")
    port: int = Field(8000, description="Server port")
    workers: int = Field(4, description="Number of worker processes")
    reload: bool = Field(False, description="Enable auto-reload for development")
    cors_origins: list[str] = Field(
        ["*"], description="CORS allowed origins for API endpoints"
    )
    request_timeout: int = Field(60, description="Request timeout in seconds")


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = Field("INFO", description="Default logging level")
    config_file: Optional[str] = Field(
        None, description="Path to logging configuration file"
    )
    log_file: Optional[str] = Field(None, description="Path to log file")


class Config(BaseModel):
    """Main configuration for the Linear MCP Server."""

    linear: LinearConfig
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    debug: bool = Field(False, description="Enable debug mode")
    environment: str = Field("production", description="Deployment environment")


def load_config(config_path: Union[str, Path]) -> Config:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to configuration YAML file

    Returns:
        Validated configuration object

    Raises:
        FileNotFoundError: If the configuration file does not exist
        ValueError: If the configuration is invalid
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as file:
        config_data: Dict[str, Any] = yaml.safe_load(file)

    # Load environment-specific configuration if it exists
    env_config_path = config_path.parent / f"{config_path.stem}.{os.getenv('ENV', 'local')}.yaml"
    if env_config_path.exists():
        with open(env_config_path, "r") as file:
            env_config_data: Dict[str, Any] = yaml.safe_load(file)
            # Merge configurations, with environment-specific config taking precedence
            config_data = _deep_merge(config_data, env_config_data)

    try:
        return Config(**config_data)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary
        override: Dictionary with values to override in base

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config_from_env() -> Config:
    """
    Load configuration from environment variables.

    Environment variables should be prefixed with LINEAR_MCP_
    and use underscore as separator for nested keys.
    
    Examples:
        LINEAR_MCP_LINEAR_API_KEY=xxx
        LINEAR_MCP_SERVER_PORT=8080
        LINEAR_MCP_LOGGING_LEVEL=DEBUG

    Returns:
        Validated configuration object with values from environment variables
    """
    # Start with minimal config requiring only the API key
    config_data = {
        "linear": {
            "api_key": os.getenv("LINEAR_MCP_LINEAR_API_KEY", ""),
        }
    }

    # Add other configuration values if present in environment
    if api_url := os.getenv("LINEAR_MCP_LINEAR_API_URL"):
        config_data["linear"]["api_url"] = api_url

    if server_host := os.getenv("LINEAR_MCP_SERVER_HOST"):
        if "server" not in config_data:
            config_data["server"] = {}
        config_data["server"]["host"] = server_host

    if server_port := os.getenv("LINEAR_MCP_SERVER_PORT"):
        if "server" not in config_data:
            config_data["server"] = {}
        config_data["server"]["port"] = int(server_port)

    if log_level := os.getenv("LINEAR_MCP_LOGGING_LEVEL"):
        if "logging" not in config_data:
            config_data["logging"] = {}
        config_data["logging"]["level"] = log_level

    if debug := os.getenv("LINEAR_MCP_DEBUG"):
        config_data["debug"] = debug.lower() in ("true", "1", "yes")

    if env := os.getenv("LINEAR_MCP_ENVIRONMENT"):
        config_data["environment"] = env

    try:
        return Config(**config_data)
    except Exception as e:
        raise ValueError(f"Invalid environment configuration: {e}")
"""
Server settings and configuration options.

This module provides classes and utilities for managing server settings,
including defaults and option validation.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class CORSSettings(BaseModel):
    """CORS configuration settings."""

    allow_origins: List[str] = Field(["*"], description="List of allowed origins")
    allow_methods: List[str] = Field(
        ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="List of allowed HTTP methods",
    )
    allow_headers: List[str] = Field(["*"], description="List of allowed HTTP headers")
    allow_credentials: bool = Field(False, description="Allow credentials")
    max_age: int = Field(600, description="Maximum age of preflight requests in seconds")


class RateLimitSettings(BaseModel):
    """Rate limiting configuration."""

    enabled: bool = Field(True, description="Enable rate limiting")
    requests_per_minute: int = Field(
        60, description="Maximum number of requests per minute per client"
    )
    burst: int = Field(
        20, description="Maximum burst size (additional requests allowed temporarily)"
    )


class LoggingSettings(BaseModel):
    """Server logging configuration."""

    request_logging: bool = Field(True, description="Log all incoming requests")
    response_logging: bool = Field(
        False, description="Log responses (can be verbose)"
    )
    log_format: str = Field(
        "standard",
        description="Log format (standard or detailed)",
    )
    
    @validator("log_format")
    def validate_log_format(cls, v: str) -> str:
        """Validate that log format is one of the allowed values."""
        if v not in ("standard", "detailed"):
            raise ValueError("Log format must be 'standard' or 'detailed'")
        return v


class SecuritySettings(BaseModel):
    """Security-related settings."""

    enable_https: bool = Field(
        False, description="Enable HTTPS (requires cert_file and key_file)"
    )
    cert_file: Optional[str] = Field(
        None, description="Path to SSL certificate file"
    )
    key_file: Optional[str] = Field(
        None, description="Path to SSL private key file"
    )
    enable_hsts: bool = Field(
        True, description="Enable HTTP Strict Transport Security"
    )
    
    @validator("enable_https")
    def validate_https_settings(cls, v: bool, values: Dict[str, Any]) -> bool:
        """Validate that cert_file and key_file are provided if HTTPS is enabled."""
        if v and (not values.get("cert_file") or not values.get("key_file")):
            raise ValueError(
                "cert_file and key_file must be provided when enable_https is True"
            )
        return v


class PerformanceSettings(BaseModel):
    """Performance-related settings."""

    worker_count: int = Field(
        0, description="Number of worker processes (0 for CPU count)"
    )
    thread_count: int = Field(
        1, description="Number of threads per worker"
    )
    backlog: int = Field(
        2048, description="Maximum number of pending connections"
    )
    timeout: int = Field(
        60, description="Request timeout in seconds"
    )
    
    @validator("worker_count")
    def validate_worker_count(cls, v: int) -> int:
        """Validate that worker_count is non-negative."""
        if v < 0:
            raise ValueError("worker_count must be non-negative")
        return v
    
    @validator("thread_count")
    def validate_thread_count(cls, v: int) -> int:
        """Validate that thread_count is positive."""
        if v <= 0:
            raise ValueError("thread_count must be positive")
        return v


class ServerSettings(BaseModel):
    """Complete server settings."""

    host: str = Field("127.0.0.1", description="Server host")
    port: int = Field(8000, description="Server port")
    debug: bool = Field(False, description="Enable debug mode")
    reload: bool = Field(False, description="Enable auto-reload for development")
    cors: CORSSettings = Field(default_factory=CORSSettings, description="CORS settings")
    rate_limit: RateLimitSettings = Field(
        default_factory=RateLimitSettings, description="Rate limiting settings"
    )
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings, description="Logging settings"
    )
    security: SecuritySettings = Field(
        default_factory=SecuritySettings, description="Security settings"
    )
    performance: PerformanceSettings = Field(
        default_factory=PerformanceSettings, description="Performance settings"
    )
    
    @validator("port")
    def validate_port(cls, v: int) -> int:
        """Validate that port is in the allowed range."""
        if not 1 <= v <= 65535:
            raise ValueError("port must be between 1 and 65535")
        return v


def create_settings_from_config(config_dict: Dict[str, Any]) -> ServerSettings:
    """
    Create server settings from a configuration dictionary.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        Validated server settings
    """
    return ServerSettings.parse_obj(config_dict)
"""
Server startup validation module.

This module provides validation checks to ensure the server can start properly.
"""

import os
import socket
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from src.config.config import Config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Exception raised when a validation check fails."""

    pass


class ServerValidator:
    """
    Validator for server startup checks.
    
    This class provides methods to validate that the server has all required
    configurations and dependencies before starting.
    """

    def __init__(self, config: Config):
        """
        Initialize the server validator.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_linear_api_key(self) -> bool:
        """
        Validate that a Linear API key is configured.
        
        Returns:
            True if valid, False otherwise
        """
        if not self.config.linear.api_key:
            self.errors.append("Linear API key is not configured")
            return False
        
        # Basic validation that it looks like an API key
        # Linear API keys are prefixed with "lin_"
        if not self.config.linear.api_key.startswith("lin_"):
            self.warnings.append(
                "Linear API key does not start with 'lin_', which is the expected format"
            )
        
        logger.debug("Linear API key validation passed")
        return True

    def validate_linear_api_connectivity(self) -> bool:
        """
        Validate connectivity to the Linear API.
        
        Returns:
            True if connectible, False otherwise
        """
        try:
            # Simple connectivity check, not a full authentication check
            response = requests.head(
                self.config.linear.api_url,
                timeout=self.config.linear.timeout,
            )
            
            # We don't care about the status, just that we can connect
            logger.debug(f"Linear API connectivity check response: {response.status_code}")
            return True
        except requests.RequestException as e:
            self.warnings.append(f"Could not connect to Linear API: {e}")
            logger.warning(f"Linear API connectivity check failed: {e}")
            return False

    def validate_port_availability(self) -> bool:
        """
        Validate that the configured port is available.
        
        Returns:
            True if available, False otherwise
        """
        host = self.config.server.host
        port = self.config.server.port
        
        try:
            # Try to bind to the configured host and port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                logger.debug(f"Port {port} is available on {host}")
                return True
        except socket.error as e:
            self.errors.append(f"Port {port} is not available on {host}: {e}")
            logger.error(f"Port validation failed: {e}")
            return False

    def validate_directory_permissions(self) -> bool:
        """
        Validate that the server has permission to write to required directories.
        
        Returns:
            True if permissions are valid, False otherwise
        """
        # Check log directory if configured
        if self.config.logging.log_file:
            log_dir = Path(self.config.logging.log_file).parent
            if not log_dir.exists():
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Created log directory: {log_dir}")
                except PermissionError as e:
                    self.errors.append(f"Cannot create log directory {log_dir}: {e}")
                    logger.error(f"Log directory permission check failed: {e}")
                    return False
            elif not os.access(log_dir, os.W_OK):
                self.errors.append(f"No write permission to log directory: {log_dir}")
                logger.error(f"Log directory permission check failed: No write permission")
                return False
        
        logger.debug("Directory permissions validation passed")
        return True

    def validate_server_configuration(self) -> bool:
        """
        Validate server configuration settings.
        
        Returns:
            True if valid, False otherwise
        """
        valid = True
        
        # Validate workers count
        if self.config.server.workers <= 0:
            self.errors.append(f"Invalid worker count: {self.config.server.workers}")
            valid = False
        
        # Validate port number
        if not 1 <= self.config.server.port <= 65535:
            self.errors.append(f"Invalid port number: {self.config.server.port}")
            valid = False
        
        # Validate request timeout
        if self.config.server.request_timeout <= 0:
            self.errors.append(f"Invalid request timeout: {self.config.server.request_timeout}")
            valid = False
        
        if not valid:
            logger.error("Server configuration validation failed")
        else:
            logger.debug("Server configuration validation passed")
        
        return valid

    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """
        Run all validation checks.
        
        Returns:
            Tuple of (success, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Run validations
        validations = [
            self.validate_linear_api_key,
            self.validate_server_configuration,
            self.validate_port_availability,
            self.validate_directory_permissions,
        ]
        
        success = True
        for validation in validations:
            if not validation():
                success = False
        
        # Run non-critical validations
        self.validate_linear_api_connectivity()
        
        if success:
            logger.info("All critical validation checks passed")
        else:
            logger.error(
                f"Validation failed with {len(self.errors)} errors and {len(self.warnings)} warnings"
            )
        
        return success, self.errors, self.warnings


def validate_server_startup(config: Config) -> None:
    """
    Validate server startup requirements and configuration.
    
    Args:
        config: Server configuration
        
    Raises:
        ValidationError: If a critical validation check fails
    """
    validator = ServerValidator(config)
    success, errors, warnings = validator.validate_all()
    
    # Log warnings
    for warning in warnings:
        logger.warning(f"Validation warning: {warning}")
    
    # If there are errors, raise exception
    if not success:
        error_message = "\n".join(errors)
        raise ValidationError(f"Server validation failed:\n{error_message}")
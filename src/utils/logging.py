"""
Logging configuration for the Linear MCP Server.

This module provides utilities for configuring logging throughout the application.
"""

import logging
import logging.config
import os
import sys
from typing import Dict, Optional, Union

import yaml


def configure_logging(
    config_path: Optional[str] = None,
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure logging for the application.

    Args:
        config_path: Path to logging configuration YAML file
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Override log file path
    """
    # Default configuration for basic logging
    default_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "detailed": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - "
                    "%(filename)s:%(lineno)d - %(message)s"
                )
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": "logs/server.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": True,
            }
        },
    }

    config: Dict[str, Union[int, Dict]] = default_config

    # Load config from file if provided
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r") as file:
                file_config = yaml.safe_load(file)
                if file_config:
                    config = file_config
        except Exception as e:
            print(f"Error loading logging config from {config_path}: {e}")
            print("Using default logging configuration")

    # Create logs directory if it doesn't exist
    if "file" in config.get("handlers", {}):
        log_directory = os.path.dirname(config["handlers"]["file"]["filename"])
        os.makedirs(log_directory, exist_ok=True)

    # Override log level if provided
    if log_level:
        numeric_level = getattr(logging, log_level.upper(), None)
        if isinstance(numeric_level, int):
            # Update root logger level
            if "" in config.get("loggers", {}):
                config["loggers"][""]["level"] = log_level.upper()
            # Update console handler level
            if "console" in config.get("handlers", {}):
                config["handlers"]["console"]["level"] = log_level.upper()

    # Override log file if provided
    if log_file and "file" in config.get("handlers", {}):
        config["handlers"]["file"]["filename"] = log_file
        log_directory = os.path.dirname(log_file)
        os.makedirs(log_directory, exist_ok=True)

    # Apply configuration
    try:
        logging.config.dictConfig(config)
    except Exception as e:
        print(f"Error configuring logging: {e}")
        print("Falling back to basic configuration")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
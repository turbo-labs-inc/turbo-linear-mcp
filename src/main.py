#!/usr/bin/env python3
"""
Linear MCP Server - Main Entry Point

This module serves as the entry point for the Linear MCP server,
initializing and starting the server with the configured settings.
"""

import argparse
import logging
import sys

# Local imports will be added as modules are implemented


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Linear MCP Server")
    parser.add_argument(
        "--config", "-c", 
        help="Path to configuration file", 
        default="config/config.yaml"
    )
    parser.add_argument(
        "--log-level", "-l",
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO"
    )
    return parser.parse_args()


def setup_logging(log_level):
    """Configure logging for the application."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def main():
    """Application entry point."""
    args = parse_arguments()
    setup_logging(args.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Linear MCP Server")
    
    # Server setup and startup will be implemented in future tasks
    logger.info("Server implementation pending")
    
    logger.info("Linear MCP Server stopped")


if __name__ == "__main__":
    main()
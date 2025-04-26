#!/usr/bin/env python3
"""
Linear MCP Server - Main Entry Point

This module serves as the entry point for the Linear MCP server,
initializing and starting the server with the configured settings.
"""

import argparse
import os
import sys
from pathlib import Path

from src.config.config import load_config
from src.server.server import create_server
from src.utils.environment import load_env_file
from src.utils.logging import configure_logging, get_logger


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
    parser.add_argument(
        "--env-file", "-e",
        help="Path to .env file",
        default=None
    )
    return parser.parse_args()


def main():
    """Application entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Load environment variables from .env file if specified
    if args.env_file:
        load_env_file(args.env_file)
    else:
        load_env_file()
    
    # Configure logging
    configure_logging(log_level=args.log_level)
    logger = get_logger(__name__)
    
    logger.info("Starting Linear MCP Server")
    
    try:
        # Load configuration
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
        
        config = load_config(config_path)
        logger.info(f"Configuration loaded from {config_path}")
        
        # Create and run server
        server = create_server(config)
        logger.info(f"Server created, listening on {config.server.host}:{config.server.port}")
        server.run()
        
    except Exception as e:
        logger.exception(f"Error starting server: {e}")
        sys.exit(1)
    
    logger.info("Linear MCP Server stopped")


if __name__ == "__main__":
    main()
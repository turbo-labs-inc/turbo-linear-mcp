"""
Server module for the Linear MCP Server.

This module provides the server implementation for handling MCP requests.
"""

import asyncio
import uuid
from typing import Any, Callable, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config.config import Config, ServerConfig
from src.server.settings import ServerSettings
from src.utils.errors import NotFoundError, setup_error_handlers
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ServerStatus(BaseModel):
    """Model representing server status information."""

    status: str
    version: str
    uptime: float
    connections: int
    environment: str


class MCPServer:
    """
    MCP Server implementation for handling Linear API requests.
    
    This class provides the core server functionality for receiving MCP requests,
    processing them, and returning responses.
    """

    def __init__(self, config: Config):
        """
        Initialize the MCP Server.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.app = FastAPI(
            title="Linear MCP Server",
            description="MCP server for integrating with Linear project management",
            version="0.1.0",
            debug=config.debug,
        )
        self._setup_middleware()
        self._setup_routes()
        self._setup_error_handlers()
        self._start_time = asyncio.get_event_loop().time()
        self._connection_count = 0
        logger.info("MCP Server initialized")

    def _setup_middleware(self) -> None:
        """Configure middleware for the FastAPI application."""
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.server.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add request logging middleware
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next: Callable) -> Response:
            """Log incoming requests and responses."""
            logger.debug(f"Request: {request.method} {request.url.path}")
            response = await call_next(request)
            logger.debug(f"Response: {response.status_code}")
            return response
        
        # Add correlation ID middleware
        @self.app.middleware("http")
        async def add_correlation_id(request: Request, call_next: Callable) -> Response:
            """Add correlation ID to requests for tracking."""
            request_id = request.headers.get("X-Request-ID")
            if not request_id:
                request_id = str(uuid.uuid4())
            
            # Set the request ID on the request state for access in route handlers
            request.state.request_id = request_id
            
            # Call the next middleware or route handler
            response = await call_next(request)
            
            # Add the request ID to the response headers
            response.headers["X-Request-ID"] = request_id
            return response

    def _setup_routes(self) -> None:
        """Configure API routes for the FastAPI application."""
        @self.app.get("/")
        async def root() -> Dict[str, str]:
            """Root endpoint returning basic server information."""
            return {
                "server": "Linear MCP Server",
                "version": "0.1.0",
                "status": "running",
            }
        
        @self.app.get("/health")
        async def health() -> Dict[str, str]:
            """Health check endpoint for monitoring."""
            return {"status": "healthy"}
        
        @self.app.get("/status")
        async def status() -> ServerStatus:
            """Status endpoint providing detailed server information."""
            current_time = asyncio.get_event_loop().time()
            uptime = current_time - self._start_time
            
            return ServerStatus(
                status="running",
                version="0.1.0",
                uptime=uptime,
                connections=self._connection_count,
                environment=self.config.environment,
            )
        
        @self.app.get("/{path:path}")
        async def catch_all(path: str) -> Dict[str, str]:
            """Catch-all route for undefined paths."""
            raise NotFoundError(f"Resource not found: {path}")

    def _setup_error_handlers(self) -> None:
        """Configure error handlers for the FastAPI application."""
        setup_error_handlers(self.app)

    def run(self) -> None:
        """Start the server using the configured settings."""
        uvicorn.run(
            app=self.app,
            host=self.config.server.host,
            port=self.config.server.port,
            workers=self.config.server.workers,
            reload=self.config.server.reload,
            log_level=self.config.logging.level.lower(),
            timeout_keep_alive=self.config.server.request_timeout,
        )


def create_server(config: Config) -> MCPServer:
    """
    Create a new MCP server instance.
    
    Args:
        config: Server configuration
        
    Returns:
        Configured MCPServer instance
    """
    return MCPServer(config)
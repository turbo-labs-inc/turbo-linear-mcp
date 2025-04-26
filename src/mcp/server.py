"""
MCP server implementation.

This module provides the core server implementation for the Model Context Protocol.
"""

import asyncio
import json
import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

import websockets
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from src.mcp.capabilities import CapabilityRegistry, CapabilityType, create_default_capabilities
from src.mcp.parser import MCPErrorCode, MCPMessage, MCPMessageType
from src.mcp.resource import ResourceProviderRegistry
from src.mcp.serializer import MCPSerializer
from src.mcp.tool import ToolProviderRegistry
from src.mcp.validation import MCPValidator
from src.mcp.version import MCPVersion, VersionNegotiator
from src.utils.errors import NotFoundError, UnauthorizedError, ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MCPConnectionState(str, Enum):
    """State of an MCP connection."""

    NEW = "new"
    INITIALIZING = "initializing"
    READY = "ready"
    CLOSING = "closing"
    CLOSED = "closed"


class MCPConnection:
    """
    Represents a connection from an MCP client.
    
    This class handles the lifecycle of a client connection, including message
    sending and receiving, and maintains connection-specific state.
    """

    def __init__(self, websocket: WebSocket, server: "MCPServer"):
        """
        Initialize a new MCP connection.
        
        Args:
            websocket: WebSocket connection
            server: MCP server instance
        """
        self.websocket = websocket
        self.server = server
        self.id = str(uuid.uuid4())
        self.state = MCPConnectionState.NEW
        self.client_info: Dict[str, Any] = {}
        self.capabilities: Dict[str, Any] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        logger.info(f"New MCP connection created: {self.id}")

    async def send_message(self, message: MCPMessage) -> None:
        """
        Send a message to the client.
        
        Args:
            message: Message to send
        """
        json_data = MCPSerializer.serialize_message(message)
        await self.websocket.send_text(json_data)
        logger.debug(f"Sent message to client {self.id}: {message.get_type()}")

    async def receive_message(self) -> MCPMessage:
        """
        Receive a message from the client.
        
        Returns:
            Received message
            
        Raises:
            ValidationError: If the received message is invalid
        """
        try:
            data = await self.websocket.receive_text()
            message = MCPMessage.parse_raw(data)
            logger.debug(f"Received message from client {self.id}: {message.get_type()}")
            return message
        except Exception as e:
            logger.error(f"Error receiving message from client {self.id}: {e}")
            raise ValidationError(f"Invalid message format: {e}")

    async def handle_initialize(self, message: MCPMessage) -> None:
        """
        Handle initialize request from client.
        
        Args:
            message: Initialize request message
        """
        if not message.params:
            error = MCPSerializer.create_error(
                message.id,
                MCPErrorCode.INVALID_PARAMS,
                "Missing required parameters for initialize request",
            )
            await self.send_message(error)
            return
        
        # Validate initialize parameters
        is_valid, error_details = MCPValidator.validate_initialize_params(message.params)
        if not is_valid:
            error = MCPSerializer.create_error(
                message.id,
                MCPErrorCode.INVALID_PARAMS,
                error_details["message"],
                error_details.get("data"),
            )
            await self.send_message(error)
            return
        
        # Store client information
        self.client_info = message.params.get("clientInfo", {})
        logger.info(
            f"Client {self.id} initialized: {self.client_info.get('name')} "
            f"{self.client_info.get('version', '')}"
        )
        
        # Negotiate capabilities
        client_capabilities = message.params.get("capabilities", {})
        self.capabilities = self.server.capability_registry.to_dict()
        
        # Create response with server information and capabilities
        response = MCPSerializer.create_initialize_response(
            message.id,
            {"name": "Linear MCP Server", "vendor": "Linear"},
            "0.1.0",
            self.capabilities,
        )
        
        # Update connection state
        self.state = MCPConnectionState.READY
        
        # Send response
        await self.send_message(response)

    async def handle_request(self, message: MCPMessage) -> None:
        """
        Handle a request message from the client.
        
        Args:
            message: Request message
        """
        method = message.method
        if not method:
            error = MCPSerializer.create_error(
                message.id,
                MCPErrorCode.INVALID_REQUEST,
                "Missing required field 'method'",
            )
            await self.send_message(error)
            return
        
        # Handle built-in methods
        if method.startswith("$/"):
            await self.handle_internal_method(message)
            return
        
        # Find method handler
        handler = self.server.get_method_handler(method)
        if not handler:
            error = MCPSerializer.create_error(
                message.id,
                MCPErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {method}",
            )
            await self.send_message(error)
            return
        
        # Execute method handler
        try:
            result = await handler(self, message.params or {})
            response = MCPSerializer.create_response(message.id, result)
            await self.send_message(response)
        except Exception as e:
            logger.error(f"Error executing method {method}: {e}")
            error = MCPSerializer.create_error(
                message.id,
                MCPErrorCode.INTERNAL_ERROR,
                f"Error executing method {method}: {str(e)}",
            )
            await self.send_message(error)

    async def handle_notification(self, message: MCPMessage) -> None:
        """
        Handle a notification message from the client.
        
        Args:
            message: Notification message
        """
        method = message.method
        if not method:
            logger.error(f"Received notification without method from client {self.id}")
            return
        
        # Handle built-in notifications
        if method == "$/close":
            await self.close()
            return
        
        # Find notification handler
        handler = self.server.get_notification_handler(method)
        if not handler:
            logger.warning(f"Notification handler not found for method: {method}")
            return
        
        # Execute notification handler
        try:
            await handler(self, message.params or {})
        except Exception as e:
            logger.error(f"Error executing notification handler for {method}: {e}")

    async def handle_internal_method(self, message: MCPMessage) -> None:
        """
        Handle internal method requests (methods starting with $/).
        
        Args:
            message: Request message
        """
        method = message.method
        
        if method == "$/cancelRequest":
            # Handle request cancellation
            if not message.params or "id" not in message.params:
                error = MCPSerializer.create_error(
                    message.id,
                    MCPErrorCode.INVALID_PARAMS,
                    "Missing required parameter 'id' for cancelRequest",
                )
                await self.send_message(error)
                return
            
            request_id = message.params["id"]
            future = self.pending_requests.get(request_id)
            if future and not future.done():
                future.cancel()
                logger.info(f"Cancelled request {request_id} for client {self.id}")
            
            response = MCPSerializer.create_response(message.id, {"cancelled": True})
            await self.send_message(response)
        
        elif method == "$/ping":
            # Simple ping method
            response = MCPSerializer.create_response(message.id, {"pong": True})
            await self.send_message(response)
        
        else:
            # Unknown internal method
            error = MCPSerializer.create_error(
                message.id,
                MCPErrorCode.METHOD_NOT_FOUND,
                f"Internal method not found: {method}",
            )
            await self.send_message(error)

    async def close(self) -> None:
        """Close the connection."""
        self.state = MCPConnectionState.CLOSING
        
        # Cancel any pending requests
        for request_id, future in self.pending_requests.items():
            if not future.done():
                future.cancel()
        
        self.pending_requests.clear()
        
        # Close the WebSocket
        try:
            await self.websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket for client {self.id}: {e}")
        
        self.state = MCPConnectionState.CLOSED
        logger.info(f"Closed connection for client {self.id}")

    def is_initialized(self) -> bool:
        """
        Check if the connection is initialized.
        
        Returns:
            True if the connection is ready for normal operation
        """
        return self.state == MCPConnectionState.READY


class MCPServer:
    """
    MCP server implementation.
    
    This class provides the core functionality for handling MCP connections
    and dispatching messages to appropriate handlers.
    """

    def __init__(self):
        """Initialize the MCP server."""
        self.connections: Dict[str, MCPConnection] = {}
        self.method_handlers: Dict[str, Callable] = {}
        self.notification_handlers: Dict[str, Callable] = {}
        
        # Initialize capabilities
        self.capability_registry = create_default_capabilities()
        
        # Initialize resource and tool registries
        self.resource_registry = ResourceProviderRegistry()
        self.tool_registry = ToolProviderRegistry()
        
        # Initialize version negotiator
        self.version_negotiator = VersionNegotiator([
            MCPVersion.V1_0,
            MCPVersion.V1_1,
            MCPVersion.V2_0,
        ])
        
        # Register built-in methods
        self.register_method("linear.convertFeatureList", self.handle_convert_feature_list)
        self.register_method("linear.search", self.handle_search)
        
        logger.info("MCP server initialized")

    def register_method(self, method: str, handler: Callable) -> None:
        """
        Register a method handler.
        
        Args:
            method: Method name
            handler: Handler function
        """
        self.method_handlers[method] = handler
        logger.debug(f"Registered method handler for {method}")

    def register_notification(self, method: str, handler: Callable) -> None:
        """
        Register a notification handler.
        
        Args:
            method: Method name
            handler: Handler function
        """
        self.notification_handlers[method] = handler
        logger.debug(f"Registered notification handler for {method}")

    def get_method_handler(self, method: str) -> Optional[Callable]:
        """
        Get a method handler by name.
        
        Args:
            method: Method name
            
        Returns:
            Handler function, or None if not found
        """
        return self.method_handlers.get(method)

    def get_notification_handler(self, method: str) -> Optional[Callable]:
        """
        Get a notification handler by name.
        
        Args:
            method: Method name
            
        Returns:
            Handler function, or None if not found
        """
        return self.notification_handlers.get(method)

    async def handle_connection(self, websocket: WebSocket) -> None:
        """
        Handle a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        
        # Create new connection object
        connection = MCPConnection(websocket, self)
        self.connections[connection.id] = connection
        
        try:
            while True:
                # Receive and process messages
                try:
                    message = await connection.receive_message()
                except ValidationError as e:
                    # Send error for invalid message format
                    error = MCPSerializer.create_error(
                        None,
                        MCPErrorCode.PARSE_ERROR,
                        str(e),
                    )
                    await connection.send_message(error)
                    continue
                
                # Process message based on type
                message_type = message.get_type()
                
                if message_type == MCPMessageType.INITIALIZE:
                    # Handle initialization request
                    await connection.handle_initialize(message)
                
                elif message_type == MCPMessageType.REQUEST:
                    # Check if connection is initialized
                    if not connection.is_initialized() and message.method != "$/ping":
                        error = MCPSerializer.create_error(
                            message.id,
                            MCPErrorCode.INVALID_REQUEST,
                            "Connection not initialized",
                        )
                        await connection.send_message(error)
                        continue
                    
                    # Handle request
                    await connection.handle_request(message)
                
                elif message_type == MCPMessageType.NOTIFICATION:
                    # Check if connection is initialized
                    if not connection.is_initialized() and message.method != "$/close":
                        logger.warning(
                            f"Received notification on uninitialized connection: {message.method}"
                        )
                        continue
                    
                    # Handle notification
                    await connection.handle_notification(message)
                
                elif message_type == MCPMessageType.CANCEL:
                    # Handle cancellation request
                    await connection.handle_internal_method(message)
                
                else:
                    # Unexpected message type
                    logger.warning(f"Unexpected message type: {message_type}")
                    continue
        
        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {connection.id}")
        except Exception as e:
            logger.error(f"Error handling connection {connection.id}: {e}")
        finally:
            # Clean up connection
            await connection.close()
            if connection.id in self.connections:
                del self.connections[connection.id]

    async def handle_convert_feature_list(self, connection: MCPConnection, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle feature list conversion request.
        
        Args:
            connection: Client connection
            params: Request parameters
            
        Returns:
            Conversion result
        """
        # Validate parameters
        if "text" not in params:
            raise ValidationError("Missing required parameter 'text'")
        
        # Get the feature list tool provider
        provider = self.tool_registry.get_provider("linear.convertFeatureList")
        if not provider:
            raise NotFoundError("Feature list conversion tool not available")
        
        # Execute the tool
        result = await provider.execute(params)
        return result

    async def handle_search(self, connection: MCPConnection, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle search request.
        
        Args:
            connection: Client connection
            params: Request parameters
            
        Returns:
            Search result
        """
        # Validate parameters
        if "query" not in params:
            raise ValidationError("Missing required parameter 'query'")
        
        # Get the search tool provider
        provider = self.tool_registry.get_provider("linear.search")
        if not provider:
            raise NotFoundError("Search tool not available")
        
        # Execute the tool
        result = await provider.execute(params)
        return result

    def setup_routes(self, app: FastAPI) -> None:
        """
        Set up FastAPI routes for the MCP server.
        
        Args:
            app: FastAPI application
        """
        @app.websocket("/mcp")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for MCP connections."""
            await self.handle_connection(websocket)


def create_mcp_server() -> MCPServer:
    """
    Create a new MCP server instance.
    
    Returns:
        Configured MCP server instance
    """
    return MCPServer()
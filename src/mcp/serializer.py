"""
MCP message serialization module.

This module provides functionality for serializing Model Context Protocol (MCP) messages.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Union

from src.mcp.parser import (
    MCPErrorCode,
    MCPErrorData,
    MCPInitializeParams,
    MCPInitializeResult,
    MCPMessage,
    MCPMessageType,
)
from src.utils.errors import ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MCPSerializer:
    """
    Serializer for MCP messages.
    
    This class provides utilities for serializing MCP messages and objects.
    """

    @staticmethod
    def serialize_message(message: MCPMessage) -> str:
        """
        Serialize an MCP message to JSON.
        
        Args:
            message: MCP message
            
        Returns:
            JSON string
        """
        return json.dumps(message.dict(exclude_none=True))

    @staticmethod
    def serialize_object(obj: Any) -> Dict[str, Any]:
        """
        Serialize an object to a dictionary suitable for JSON serialization.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Dictionary representation of the object
        """
        if hasattr(obj, "dict"):
            return obj.dict(exclude_none=True)
        elif isinstance(obj, dict):
            return obj
        elif isinstance(obj, list):
            return [MCPSerializer.serialize_object(item) for item in obj]
        else:
            return obj

    @staticmethod
    def create_message_id() -> str:
        """
        Generate a unique message ID.
        
        Returns:
            Unique message ID
        """
        return str(uuid.uuid4())

    @staticmethod
    def create_initialize_response(
        request_id: Union[str, int],
        server_info: Dict[str, str],
        server_version: str,
        capabilities: Dict[str, Any],
    ) -> MCPMessage:
        """
        Create an initialize response message.
        
        Args:
            request_id: Request ID
            server_info: Server information
            server_version: Server version
            capabilities: Server capabilities
            
        Returns:
            Initialize response message
        """
        result = MCPInitializeResult(
            server_info=server_info,
            server_version=server_version,
            capabilities=capabilities,
        )
        
        return MCPMessage(
            id=request_id,
            result=result.dict(exclude_none=True),
        )

    @staticmethod
    def create_request(
        method: str,
        params: Optional[Dict[str, Any]] = None,
        message_id: Optional[Union[str, int]] = None,
    ) -> MCPMessage:
        """
        Create a request message.
        
        Args:
            method: Method name
            params: Optional parameters
            message_id: Optional message ID (generated if not provided)
            
        Returns:
            Request message
        """
        if message_id is None:
            message_id = MCPSerializer.create_message_id()
        
        return MCPMessage(
            id=message_id,
            method=method,
            params=params,
        )

    @staticmethod
    def create_response(
        request_id: Union[str, int],
        result: Any,
    ) -> MCPMessage:
        """
        Create a response message.
        
        Args:
            request_id: Request ID
            result: Response result
            
        Returns:
            Response message
        """
        serialized_result = MCPSerializer.serialize_object(result)
        
        return MCPMessage(
            id=request_id,
            result=serialized_result,
        )

    @staticmethod
    def create_error(
        request_id: Optional[Union[str, int]],
        code: MCPErrorCode,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> MCPMessage:
        """
        Create an error message.
        
        Args:
            request_id: Request ID
            code: Error code
            message: Error message
            data: Optional error data
            
        Returns:
            Error message
        """
        return MCPMessage(
            id=request_id,
            error=MCPErrorData(
                code=code.value,
                message=message,
                data=data,
            ),
        )

    @staticmethod
    def create_notification(
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> MCPMessage:
        """
        Create a notification message.
        
        Args:
            method: Method name
            params: Optional parameters
            
        Returns:
            Notification message
        """
        return MCPMessage(
            method=method,
            params=params,
        )

    @staticmethod
    def create_cancel_request(request_id: Union[str, int]) -> MCPMessage:
        """
        Create a cancel request message.
        
        Args:
            request_id: ID of the request to cancel
            
        Returns:
            Cancel request message
        """
        return MCPMessage(
            method="$/cancelRequest",
            params={"id": request_id},
        )

    @staticmethod
    def create_close_notification() -> MCPMessage:
        """
        Create a close notification message.
        
        Returns:
            Close notification message
        """
        return MCPMessage(
            method="$/close",
        )
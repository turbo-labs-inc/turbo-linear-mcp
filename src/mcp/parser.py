"""
MCP message parser module.

This module provides functionality for parsing Model Context Protocol (MCP) messages.
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

from src.utils.errors import ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MCPMessageType(str, Enum):
    """Types of MCP messages."""

    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    NOTIFICATION = "notification"
    CANCEL = "cancel"
    CLOSE = "close"


class MCPErrorCode(int, Enum):
    """Error codes for MCP error messages."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR_START = -32099
    SERVER_ERROR_END = -32000


class MCPErrorData(BaseModel):
    """Data for MCP error messages."""

    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class MCPMessage(BaseModel):
    """Base model for all MCP messages."""

    jsonrpc: str = Field("2.0", description="JSON-RPC version, must be 2.0")
    id: Optional[Union[str, int]] = Field(None, description="Message ID")
    method: Optional[str] = Field(None, description="Method name")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")
    result: Optional[Any] = Field(None, description="Method result")
    error: Optional[MCPErrorData] = Field(None, description="Error information")
    
    @validator("jsonrpc")
    def validate_jsonrpc(cls, v: str) -> str:
        """Validate JSON-RPC version."""
        if v != "2.0":
            raise ValueError("JSON-RPC version must be 2.0")
        return v
    
    def get_type(self) -> MCPMessageType:
        """Determine the message type based on its content."""
        if self.method is not None:
            if self.method == "initialize":
                return MCPMessageType.INITIALIZE
            elif self.method == "$/cancelRequest":
                return MCPMessageType.CANCEL
            else:
                return MCPMessageType.REQUEST
        elif self.result is not None:
            if "capabilities" in self.result:
                return MCPMessageType.INITIALIZED
            else:
                return MCPMessageType.RESPONSE
        elif self.error is not None:
            return MCPMessageType.ERROR
        else:
            # Default to notification if none of the above
            return MCPMessageType.NOTIFICATION


class MCPInitializeParams(BaseModel):
    """Parameters for initialize request."""

    client_info: Dict[str, str] = Field(..., description="Client information")
    client_version: str = Field(..., description="Client version")
    capabilities: Dict[str, Any] = Field(..., description="Client capabilities")
    trace: Optional[str] = Field(None, description="Trace level")


class MCPInitializeResult(BaseModel):
    """Result for initialize response."""

    server_info: Dict[str, str] = Field(..., description="Server information")
    server_version: str = Field(..., description="Server version")
    capabilities: Dict[str, Any] = Field(..., description="Server capabilities")


class MCPParser:
    """
    Parser for MCP messages.
    
    This class provides utilities for parsing and validating MCP messages.
    """

    @staticmethod
    def parse(message_json: str) -> MCPMessage:
        """
        Parse an MCP message from JSON.
        
        Args:
            message_json: JSON string containing an MCP message
            
        Returns:
            Parsed MCP message
            
        Raises:
            ValidationError: If the message is invalid
        """
        try:
            data = json.loads(message_json)
            message = MCPMessage.parse_obj(data)
            return message
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MCP message: {e}")
            raise ValidationError(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to validate MCP message: {e}")
            raise ValidationError(f"Invalid MCP message: {e}")

    @staticmethod
    def parse_initialize_params(params: Dict[str, Any]) -> MCPInitializeParams:
        """
        Parse initialize request parameters.
        
        Args:
            params: Parameter dictionary
            
        Returns:
            Parsed initialize parameters
            
        Raises:
            ValidationError: If the parameters are invalid
        """
        try:
            return MCPInitializeParams.parse_obj(params)
        except Exception as e:
            logger.error(f"Failed to parse initialize parameters: {e}")
            raise ValidationError(f"Invalid initialize parameters: {e}")

    @staticmethod
    def parse_initialize_result(result: Dict[str, Any]) -> MCPInitializeResult:
        """
        Parse initialize response result.
        
        Args:
            result: Result dictionary
            
        Returns:
            Parsed initialize result
            
        Raises:
            ValidationError: If the result is invalid
        """
        try:
            return MCPInitializeResult.parse_obj(result)
        except Exception as e:
            logger.error(f"Failed to parse initialize result: {e}")
            raise ValidationError(f"Invalid initialize result: {e}")

    @staticmethod
    def serialize(message: MCPMessage) -> str:
        """
        Serialize an MCP message to JSON.
        
        Args:
            message: MCP message
            
        Returns:
            JSON string
        """
        return message.json(exclude_none=True)

    @staticmethod
    def create_error_message(
        message_id: Optional[Union[str, int]],
        code: MCPErrorCode,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> MCPMessage:
        """
        Create an MCP error message.
        
        Args:
            message_id: Message ID
            code: Error code
            message: Error message
            data: Optional error data
            
        Returns:
            MCP error message
        """
        return MCPMessage(
            id=message_id,
            error=MCPErrorData(
                code=code.value,
                message=message,
                data=data,
            ),
        )

    @staticmethod
    def create_response_message(
        message_id: Union[str, int],
        result: Any,
    ) -> MCPMessage:
        """
        Create an MCP response message.
        
        Args:
            message_id: Message ID
            result: Response result
            
        Returns:
            MCP response message
        """
        return MCPMessage(
            id=message_id,
            result=result,
        )

    @staticmethod
    def create_notification_message(
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> MCPMessage:
        """
        Create an MCP notification message.
        
        Args:
            method: Method name
            params: Optional parameters
            
        Returns:
            MCP notification message
        """
        return MCPMessage(
            method=method,
            params=params,
        )

    @staticmethod
    def create_request_message(
        message_id: Union[str, int],
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> MCPMessage:
        """
        Create an MCP request message.
        
        Args:
            message_id: Message ID
            method: Method name
            params: Optional parameters
            
        Returns:
            MCP request message
        """
        return MCPMessage(
            id=message_id,
            method=method,
            params=params,
        )
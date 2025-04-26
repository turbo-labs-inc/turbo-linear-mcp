"""
MCP message validation utilities.

This module provides utilities for validating MCP messages and parameters.
"""

from typing import Any, Dict, List, Optional, Tuple, Union

from jsonschema import FormatChecker, ValidationError, validate

from src.mcp.parser import MCPErrorCode, MCPMessage, MCPMessageType
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MCPValidator:
    """
    Validator for MCP messages and parameters.
    
    This class provides utilities for validating messages against JSON schemas.
    """

    @staticmethod
    def validate_message(message: MCPMessage) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate an MCP message structure.
        
        Args:
            message: MCP message to validate
            
        Returns:
            Tuple of (is_valid, error_details)
        """
        # Basic message structure validation
        basic_schema = {
            "type": "object",
            "required": ["jsonrpc"],
            "properties": {
                "jsonrpc": {"type": "string", "enum": ["2.0"]},
                "id": {"type": ["string", "number", "null"]},
                "method": {"type": "string"},
                "params": {"type": "object"},
                "result": {},
                "error": {
                    "type": "object",
                    "required": ["code", "message"],
                    "properties": {
                        "code": {"type": "number"},
                        "message": {"type": "string"},
                        "data": {},
                    },
                },
            },
            "oneOf": [
                {"required": ["method"]},  # Request or notification
                {"required": ["result"]},  # Success response
                {"required": ["error"]},   # Error response
            ],
        }
        
        try:
            validate(instance=message.dict(exclude_none=True), schema=basic_schema)
            return True, None
        except ValidationError as e:
            logger.error(f"Message validation error: {e}")
            return False, {
                "code": MCPErrorCode.INVALID_REQUEST.value,
                "message": f"Invalid message format: {e.message}",
                "data": {"path": list(e.path), "schema_path": list(e.schema_path)}
            }

    @staticmethod
    def validate_request_params(
        method: str, params: Dict[str, Any], schema: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate request parameters against a JSON schema.
        
        Args:
            method: Method name
            params: Parameters to validate
            schema: JSON schema for validation
            
        Returns:
            Tuple of (is_valid, error_details)
        """
        try:
            validate(instance=params, schema=schema, format_checker=FormatChecker())
            return True, None
        except ValidationError as e:
            logger.error(f"Parameter validation error for method '{method}': {e}")
            return False, {
                "code": MCPErrorCode.INVALID_PARAMS.value,
                "message": f"Invalid parameters for method '{method}': {e.message}",
                "data": {"path": list(e.path), "schema_path": list(e.schema_path)}
            }

    @staticmethod
    def validate_initialize_params(params: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate parameters for the initialize method.
        
        Args:
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_details)
        """
        schema = {
            "type": "object",
            "required": ["clientInfo", "capabilities"],
            "properties": {
                "clientInfo": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                    },
                },
                "capabilities": {
                    "type": "object",
                },
                "trace": {
                    "type": "string",
                    "enum": ["off", "messages", "verbose"],
                },
            },
        }
        
        return MCPValidator.validate_request_params("initialize", params, schema)

    @staticmethod
    def validate_request(message: MCPMessage) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate a request message.
        
        Args:
            message: Request message to validate
            
        Returns:
            Tuple of (is_valid, error_details)
        """
        # First validate message structure
        is_valid, error_details = MCPValidator.validate_message(message)
        if not is_valid:
            return is_valid, error_details
        
        # For request messages, method and id are required
        if message.method is None:
            return False, {
                "code": MCPErrorCode.INVALID_REQUEST.value,
                "message": "Missing required field 'method' for request message",
            }
        
        if message.id is None:
            return False, {
                "code": MCPErrorCode.INVALID_REQUEST.value,
                "message": "Missing required field 'id' for request message",
            }
        
        return True, None

    @staticmethod
    def validate_notification(message: MCPMessage) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate a notification message.
        
        Args:
            message: Notification message to validate
            
        Returns:
            Tuple of (is_valid, error_details)
        """
        # First validate message structure
        is_valid, error_details = MCPValidator.validate_message(message)
        if not is_valid:
            return is_valid, error_details
        
        # For notification messages, method is required and id must be absent
        if message.method is None:
            return False, {
                "code": MCPErrorCode.INVALID_REQUEST.value,
                "message": "Missing required field 'method' for notification message",
            }
        
        if message.id is not None:
            return False, {
                "code": MCPErrorCode.INVALID_REQUEST.value,
                "message": "Field 'id' must be absent for notification message",
            }
        
        return True, None

    @staticmethod
    def validate_response(message: MCPMessage) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate a response message.
        
        Args:
            message: Response message to validate
            
        Returns:
            Tuple of (is_valid, error_details)
        """
        # First validate message structure
        is_valid, error_details = MCPValidator.validate_message(message)
        if not is_valid:
            return is_valid, error_details
        
        # For response messages, id is required and either result or error must be present
        if message.id is None:
            return False, {
                "code": MCPErrorCode.INVALID_REQUEST.value,
                "message": "Missing required field 'id' for response message",
            }
        
        if message.result is None and message.error is None:
            return False, {
                "code": MCPErrorCode.INVALID_REQUEST.value,
                "message": "Either 'result' or 'error' must be present for response message",
            }
        
        if message.result is not None and message.error is not None:
            return False, {
                "code": MCPErrorCode.INVALID_REQUEST.value,
                "message": "Only one of 'result' or 'error' must be present for response message",
            }
        
        return True, None
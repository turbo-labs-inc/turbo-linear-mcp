"""
Tests for the MCP message parser module.
"""

import json
import pytest

from src.mcp.parser import (
    MCPErrorCode,
    MCPInitializeParams,
    MCPInitializeResult,
    MCPMessage,
    MCPMessageType,
    MCPParser,
)
from src.utils.errors import ValidationError


def test_mcp_message_model():
    """Test the MCP message model."""
    # Test request message
    request = MCPMessage(
        jsonrpc="2.0",
        id="test-id",
        method="test.method",
        params={"param1": "value1"},
    )
    
    assert request.jsonrpc == "2.0"
    assert request.id == "test-id"
    assert request.method == "test.method"
    assert request.params == {"param1": "value1"}
    assert request.result is None
    assert request.error is None
    
    # Test response message
    response = MCPMessage(
        jsonrpc="2.0",
        id="test-id",
        result={"result1": "value1"},
    )
    
    assert response.jsonrpc == "2.0"
    assert response.id == "test-id"
    assert response.method is None
    assert response.params is None
    assert response.result == {"result1": "value1"}
    assert response.error is None
    
    # Test error message
    error = MCPMessage(
        jsonrpc="2.0",
        id="test-id",
        error={"code": -32600, "message": "Invalid request"},
    )
    
    assert error.jsonrpc == "2.0"
    assert error.id == "test-id"
    assert error.method is None
    assert error.params is None
    assert error.result is None
    assert error.error == {"code": -32600, "message": "Invalid request"}


def test_mcp_message_get_type():
    """Test the message type detection."""
    # Test initialize message
    initialize = MCPMessage(
        jsonrpc="2.0",
        id="test-id",
        method="initialize",
        params={"clientInfo": {"name": "test"}, "capabilities": {}},
    )
    assert initialize.get_type() == MCPMessageType.INITIALIZE
    
    # Test initialized message
    initialized = MCPMessage(
        jsonrpc="2.0",
        id="test-id",
        result={"capabilities": {}},
    )
    assert initialized.get_type() == MCPMessageType.INITIALIZED
    
    # Test request message
    request = MCPMessage(
        jsonrpc="2.0",
        id="test-id",
        method="test.method",
        params={"param1": "value1"},
    )
    assert request.get_type() == MCPMessageType.REQUEST
    
    # Test response message
    response = MCPMessage(
        jsonrpc="2.0",
        id="test-id",
        result={"result1": "value1"},
    )
    assert response.get_type() == MCPMessageType.RESPONSE
    
    # Test error message
    error = MCPMessage(
        jsonrpc="2.0",
        id="test-id",
        error={"code": -32600, "message": "Invalid request"},
    )
    assert error.get_type() == MCPMessageType.ERROR
    
    # Test notification message
    notification = MCPMessage(
        jsonrpc="2.0",
        method="test.notification",
        params={"param1": "value1"},
    )
    assert notification.get_type() == MCPMessageType.NOTIFICATION
    
    # Test cancel message
    cancel = MCPMessage(
        jsonrpc="2.0",
        id="test-id",
        method="$/cancelRequest",
        params={"id": "request-id"},
    )
    assert cancel.get_type() == MCPMessageType.CANCEL


def test_mcp_parser_parse():
    """Test parsing MCP messages from JSON."""
    # Test parsing a valid message
    message_json = json.dumps({
        "jsonrpc": "2.0",
        "id": "test-id",
        "method": "test.method",
        "params": {"param1": "value1"}
    })
    
    message = MCPParser.parse(message_json)
    assert message.id == "test-id"
    assert message.method == "test.method"
    assert message.params == {"param1": "value1"}
    
    # Test parsing an invalid JSON
    with pytest.raises(ValidationError):
        MCPParser.parse("{invalid json")
    
    # Test parsing an invalid message (missing jsonrpc)
    with pytest.raises(ValidationError):
        MCPParser.parse('{"id": "test-id", "method": "test.method"}')


def test_parse_initialize_params():
    """Test parsing initialize parameters."""
    # Test parsing valid parameters
    params = {
        "clientInfo": {"name": "test-client", "version": "1.0"},
        "capabilities": {"testCapability": {}},
        "trace": "off"
    }
    
    result = MCPParser.parse_initialize_params(params)
    assert isinstance(result, MCPInitializeParams)
    assert result.client_info == {"name": "test-client", "version": "1.0"}
    assert result.capabilities == {"testCapability": {}}
    assert result.trace == "off"
    
    # Test parsing invalid parameters
    with pytest.raises(ValidationError):
        MCPParser.parse_initialize_params({"invalid": "params"})


def test_parse_initialize_result():
    """Test parsing initialize result."""
    # Test parsing valid result
    result_data = {
        "server_info": {"name": "test-server", "version": "1.0"},
        "server_version": "1.0",
        "capabilities": {"testCapability": {}}
    }
    
    result = MCPParser.parse_initialize_result(result_data)
    assert isinstance(result, MCPInitializeResult)
    assert result.server_info == {"name": "test-server", "version": "1.0"}
    assert result.server_version == "1.0"
    assert result.capabilities == {"testCapability": {}}
    
    # Test parsing invalid result
    with pytest.raises(ValidationError):
        MCPParser.parse_initialize_result({"invalid": "result"})


def test_serialize():
    """Test serializing MCP messages to JSON."""
    message = MCPMessage(
        jsonrpc="2.0",
        id="test-id",
        method="test.method",
        params={"param1": "value1"},
    )
    
    serialized = MCPParser.serialize(message)
    deserialized = json.loads(serialized)
    
    assert deserialized["jsonrpc"] == "2.0"
    assert deserialized["id"] == "test-id"
    assert deserialized["method"] == "test.method"
    assert deserialized["params"] == {"param1": "value1"}
    assert "result" not in deserialized
    assert "error" not in deserialized


def test_create_error_message():
    """Test creating error messages."""
    error = MCPParser.create_error_message(
        "test-id",
        MCPErrorCode.INVALID_REQUEST,
        "Invalid request",
        {"detail": "test detail"},
    )
    
    assert error.id == "test-id"
    assert error.error.code == MCPErrorCode.INVALID_REQUEST.value
    assert error.error.message == "Invalid request"
    assert error.error.data == {"detail": "test detail"}


def test_create_response_message():
    """Test creating response messages."""
    response = MCPParser.create_response_message(
        "test-id",
        {"result1": "value1"},
    )
    
    assert response.id == "test-id"
    assert response.result == {"result1": "value1"}
    assert response.error is None


def test_create_notification_message():
    """Test creating notification messages."""
    notification = MCPParser.create_notification_message(
        "test.notification",
        {"param1": "value1"},
    )
    
    assert notification.id is None
    assert notification.method == "test.notification"
    assert notification.params == {"param1": "value1"}
    assert notification.result is None
    assert notification.error is None


def test_create_request_message():
    """Test creating request messages."""
    request = MCPParser.create_request_message(
        "test-id",
        "test.method",
        {"param1": "value1"},
    )
    
    assert request.id == "test-id"
    assert request.method == "test.method"
    assert request.params == {"param1": "value1"}
    assert request.result is None
    assert request.error is None
"""
MCP capability declaration module.

This module provides functionality for declaring and negotiating MCP capabilities
between client and server.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from src.mcp.version import MCPVersion
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CapabilityType(str, Enum):
    """Types of MCP capabilities."""

    RESOURCE = "resource"
    TOOL = "tool"
    FEATURE = "feature"


class CapabilityOption(BaseModel):
    """Model representing an option for a capability."""

    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    pattern: Optional[str] = None


class Capability(BaseModel):
    """Model representing an MCP capability."""

    name: str
    type: CapabilityType
    description: Optional[str] = None
    version: Optional[str] = None
    options: Optional[Dict[str, CapabilityOption]] = None
    metadata: Optional[Dict[str, Any]] = None

    def matches(self, client_capability: "Capability") -> bool:
        """
        Check if this capability matches a client capability.
        
        Args:
            client_capability: Client capability to check against
            
        Returns:
            True if the capabilities match, False otherwise
        """
        # Must match name and type
        if self.name != client_capability.name or self.type != client_capability.type:
            return False
        
        # If versions are specified, they must be compatible
        if self.version and client_capability.version and self.version != client_capability.version:
            return False
        
        return True


class ResourceCapability(Capability):
    """Model representing a resource capability."""

    type: CapabilityType = CapabilityType.RESOURCE
    operations: List[str] = Field(..., description="Operations supported by this resource")

    def supports_operation(self, operation: str) -> bool:
        """
        Check if this resource supports a specific operation.
        
        Args:
            operation: Operation to check
            
        Returns:
            True if the operation is supported, False otherwise
        """
        return operation in self.operations


class ToolCapability(Capability):
    """Model representing a tool capability."""

    type: CapabilityType = CapabilityType.TOOL
    command: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None


class FeatureCapability(Capability):
    """Model representing a feature capability."""

    type: CapabilityType = CapabilityType.FEATURE
    settings: Optional[Dict[str, Any]] = None


class CapabilityRegistry:
    """
    Registry for MCP capabilities.
    
    This class maintains a registry of capabilities supported by the server.
    """

    def __init__(self):
        """Initialize the capability registry."""
        self.capabilities: Dict[str, Capability] = {}
        logger.info("Capability registry initialized")

    def register_capability(self, capability: Capability) -> None:
        """
        Register a capability with the registry.
        
        Args:
            capability: Capability to register
        """
        self.capabilities[capability.name] = capability
        logger.debug(f"Registered capability: {capability.name} ({capability.type})")

    def get_capability(self, name: str) -> Optional[Capability]:
        """
        Get a registered capability by name.
        
        Args:
            name: Capability name
            
        Returns:
            Capability, or None if not found
        """
        return self.capabilities.get(name)

    def has_capability(self, name: str) -> bool:
        """
        Check if a capability is registered.
        
        Args:
            name: Capability name
            
        Returns:
            True if the capability is registered, False otherwise
        """
        return name in self.capabilities

    def get_capabilities_by_type(self, capability_type: CapabilityType) -> List[Capability]:
        """
        Get all registered capabilities of a specific type.
        
        Args:
            capability_type: Capability type
            
        Returns:
            List of capabilities of the specified type
        """
        return [
            capability
            for capability in self.capabilities.values()
            if capability.type == capability_type
        ]

    def get_all_capabilities(self) -> List[Capability]:
        """
        Get all registered capabilities.
        
        Returns:
            List of all capabilities
        """
        return list(self.capabilities.values())

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Convert the registry to a dictionary suitable for JSON serialization.
        
        Returns:
            Dictionary of capabilities
        """
        return {
            name: capability.dict(exclude_none=True)
            for name, capability in self.capabilities.items()
        }


class CapabilityNegotiator:
    """
    Negotiator for MCP capabilities.
    
    This class handles capability negotiation between client and server.
    """

    def __init__(self, server_registry: CapabilityRegistry):
        """
        Initialize the capability negotiator.
        
        Args:
            server_registry: Registry of server capabilities
        """
        self.server_registry = server_registry
        logger.info("Capability negotiator initialized")

    def negotiate_capabilities(
        self, client_capabilities: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Negotiate capabilities between client and server.
        
        Args:
            client_capabilities: Dictionary of client capabilities
            
        Returns:
            Dictionary of negotiated capabilities
        """
        negotiated_capabilities: Dict[str, Dict[str, Any]] = {}
        
        # Go through server capabilities and find matches with client
        for name, capability in self.server_registry.capabilities.items():
            if name in client_capabilities:
                # Convert client capability dict to object for easier comparison
                client_capability_dict = client_capabilities[name]
                
                # Basic type matching
                if "type" in client_capability_dict:
                    client_type = client_capability_dict["type"]
                    if client_type != capability.type:
                        logger.warning(
                            f"Capability type mismatch for {name}: "
                            f"server={capability.type}, client={client_type}"
                        )
                        continue
                
                # Include this capability in negotiated set
                negotiated_capabilities[name] = capability.dict(exclude_none=True)
                logger.debug(f"Negotiated capability: {name}")
        
        logger.info(
            f"Negotiated {len(negotiated_capabilities)} capabilities "
            f"out of {len(self.server_registry.capabilities)} server capabilities "
            f"and {len(client_capabilities)} client capabilities"
        )
        
        return negotiated_capabilities

    def get_required_capabilities(self) -> Set[str]:
        """
        Get the set of required capabilities.
        
        Returns:
            Set of required capability names
        """
        # Currently, all capabilities are optional
        return set()


# Create default capabilities for Linear MCP server
def create_default_capabilities() -> CapabilityRegistry:
    """
    Create default capabilities for the Linear MCP server.
    
    Returns:
        Capability registry with default capabilities
    """
    registry = CapabilityRegistry()
    
    # Linear resources
    registry.register_capability(
        ResourceCapability(
            name="linear.issue",
            description="Linear issue resource",
            operations=["list", "get", "create", "update", "delete"],
        )
    )
    
    registry.register_capability(
        ResourceCapability(
            name="linear.project",
            description="Linear project resource",
            operations=["list", "get"],
        )
    )
    
    registry.register_capability(
        ResourceCapability(
            name="linear.team",
            description="Linear team resource",
            operations=["list", "get"],
        )
    )
    
    registry.register_capability(
        ResourceCapability(
            name="linear.user",
            description="Linear user resource",
            operations=["list", "get"],
        )
    )
    
    # Linear tools
    registry.register_capability(
        ToolCapability(
            name="linear.convertFeatureList",
            description="Convert a feature list to Linear issues",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "format": {"type": "string", "enum": ["text", "markdown", "json"]},
                    "teamId": {"type": "string"},
                    "projectId": {"type": "string"},
                    "labels": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "url": {"type": "string"},
                            },
                        },
                    }
                },
            },
        )
    )
    
    registry.register_capability(
        ToolCapability(
            name="linear.search",
            description="Search Linear resources",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "resourceTypes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "limit": {"type": "integer"},
                    "offset": {"type": "integer"},
                },
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "url": {"type": "string"},
                            },
                        },
                    },
                    "totalCount": {"type": "integer"},
                },
            },
        )
    )
    
    # Feature capabilities
    registry.register_capability(
        FeatureCapability(
            name="textDocument",
            description="Text document synchronization",
            settings={
                "synchronization": True,
                "completion": False,
                "hover": False,
                "signatureHelp": False,
                "declaration": False,
                "definition": False,
                "references": False,
                "documentHighlight": False,
                "documentSymbol": False,
                "codeAction": False,
                "codeLens": False,
                "formatting": False,
            },
        )
    )
    
    return registry
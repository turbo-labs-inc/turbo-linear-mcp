"""
MCP tool provider interface.

This module defines the interface for MCP tool providers, which implement
tools that can be used by MCP clients.
"""

import abc
import json
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ToolSchema(BaseModel):
    """Model representing a tool's schema."""

    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class ToolMetadata(BaseModel):
    """Model representing tool metadata."""

    name: str
    description: str
    schema: ToolSchema
    version: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


class ToolProvider(abc.ABC):
    """
    Abstract base class for MCP tool providers.
    
    Tool providers implement specific functionality that can be exposed to MCP clients.
    """

    @abc.abstractmethod
    async def get_metadata(self) -> ToolMetadata:
        """
        Get metadata about this tool.
        
        Returns:
            Tool metadata
        """
        pass

    @abc.abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with the given parameters.
        
        Args:
            params: Tool parameters
            
        Returns:
            Tool result
        """
        pass

    async def validate_input(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the input parameters against the tool's schema.
        
        Args:
            params: Tool parameters
            
        Returns:
            Validated parameters
            
        Raises:
            ValidationError: If the parameters are invalid
        """
        metadata = await self.get_metadata()
        schema = metadata.schema.input_schema
        
        try:
            from jsonschema import validate
            validate(instance=params, schema=schema)
            return params
        except ImportError:
            logger.warning("jsonschema not installed, skipping schema validation")
            return params
        except Exception as e:
            logger.error(f"Input validation error: {e}")
            raise ValidationError(f"Invalid input parameters: {e}")

    async def validate_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the output result against the tool's schema.
        
        Args:
            result: Tool result
            
        Returns:
            Validated result
            
        Raises:
            ValidationError: If the result is invalid
        """
        metadata = await self.get_metadata()
        schema = metadata.schema.output_schema
        
        try:
            from jsonschema import validate
            validate(instance=result, schema=schema)
            return result
        except ImportError:
            logger.warning("jsonschema not installed, skipping schema validation")
            return result
        except Exception as e:
            logger.error(f"Output validation error: {e}")
            raise ValidationError(f"Invalid output result: {e}")


class ToolProviderRegistry:
    """
    Registry for MCP tool providers.
    
    This class maintains a registry of tool providers available to the server.
    """

    def __init__(self):
        """Initialize the tool provider registry."""
        self.providers: Dict[str, ToolProvider] = {}
        logger.info("Tool provider registry initialized")

    def register_provider(self, name: str, provider: ToolProvider) -> None:
        """
        Register a tool provider.
        
        Args:
            name: Tool name
            provider: Tool provider to register
        """
        self.providers[name] = provider
        logger.debug(f"Registered tool provider for {name}")

    def get_provider(self, name: str) -> Optional[ToolProvider]:
        """
        Get a registered tool provider by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool provider, or None if not found
        """
        return self.providers.get(name)

    def has_provider(self, name: str) -> bool:
        """
        Check if a provider is registered for a tool.
        
        Args:
            name: Tool name
            
        Returns:
            True if a provider is registered, False otherwise
        """
        return name in self.providers

    def get_all_providers(self) -> Dict[str, ToolProvider]:
        """
        Get all registered tool providers.
        
        Returns:
            Dictionary of tool name to provider
        """
        return self.providers

    async def get_all_metadata(self) -> Dict[str, ToolMetadata]:
        """
        Get metadata for all registered tools.
        
        Returns:
            Dictionary of tool name to metadata
        """
        metadata = {}
        for name, provider in self.providers.items():
            try:
                metadata[name] = await provider.get_metadata()
            except Exception as e:
                logger.error(f"Error getting metadata for tool {name}: {e}")
        
        return metadata
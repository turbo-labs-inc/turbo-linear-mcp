"""
MCP resource provider interface.

This module defines the interface for MCP resource providers, which handle
operations on resources like issues, projects, and teams.
"""

import abc
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from src.utils.errors import NotFoundError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ResourceOperation(str, Enum):
    """Types of operations that can be performed on resources."""

    LIST = "list"
    GET = "get"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"


class ResourceType(str, Enum):
    """Types of resources that can be provided."""

    ISSUE = "issue"
    PROJECT = "project"
    TEAM = "team"
    USER = "user"
    COMMENT = "comment"
    LABEL = "label"
    CUSTOM_FIELD = "customField"
    WORKFLOW_STATE = "workflowState"
    CYCLE = "cycle"


class ResourceIdentifier(BaseModel):
    """Model representing a resource identifier."""

    id: str
    type: ResourceType


class ResourceFilter(BaseModel):
    """Base model for resource filters."""

    field: str
    operator: str
    value: Any


class ResourcePage(BaseModel):
    """Model representing a page of resources."""

    items: List[Dict[str, Any]]
    total_count: int
    has_more: bool
    cursor: Optional[str] = None


class ResourceProvider(abc.ABC):
    """
    Abstract base class for MCP resource providers.
    
    Resource providers handle operations on specific types of resources.
    """

    @abc.abstractmethod
    async def get_resource_type(self) -> ResourceType:
        """
        Get the type of resource provided by this provider.
        
        Returns:
            Resource type
        """
        pass

    @abc.abstractmethod
    async def get_supported_operations(self) -> List[ResourceOperation]:
        """
        Get the operations supported by this provider.
        
        Returns:
            List of supported operations
        """
        pass

    @abc.abstractmethod
    async def list_resources(
        self,
        filters: Optional[List[ResourceFilter]] = None,
        page_size: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> ResourcePage:
        """
        List resources matching the given filters.
        
        Args:
            filters: Optional filters to apply
            page_size: Optional page size
            cursor: Optional cursor for pagination
            
        Returns:
            Page of resources
        """
        pass

    @abc.abstractmethod
    async def get_resource(self, resource_id: str) -> Dict[str, Any]:
        """
        Get a specific resource by ID.
        
        Args:
            resource_id: Resource ID
            
        Returns:
            Resource data
            
        Raises:
            NotFoundError: If the resource is not found
        """
        pass

    @abc.abstractmethod
    async def create_resource(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new resource.
        
        Args:
            data: Resource data
            
        Returns:
            Created resource data
        """
        pass

    @abc.abstractmethod
    async def update_resource(self, resource_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing resource.
        
        Args:
            resource_id: Resource ID
            data: Updated resource data
            
        Returns:
            Updated resource data
            
        Raises:
            NotFoundError: If the resource is not found
        """
        pass

    @abc.abstractmethod
    async def delete_resource(self, resource_id: str) -> None:
        """
        Delete a resource.
        
        Args:
            resource_id: Resource ID
            
        Raises:
            NotFoundError: If the resource is not found
        """
        pass

    @abc.abstractmethod
    async def query_resources(
        self, query: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Query resources using a query string.
        
        Args:
            query: Query string
            limit: Optional maximum number of results
            offset: Optional offset for pagination
            
        Returns:
            Tuple of (results, total count)
        """
        pass


class ResourceProviderRegistry:
    """
    Registry for MCP resource providers.
    
    This class maintains a registry of resource providers available to the server.
    """

    def __init__(self):
        """Initialize the resource provider registry."""
        self.providers: Dict[ResourceType, ResourceProvider] = {}
        logger.info("Resource provider registry initialized")

    def register_provider(self, provider: ResourceProvider) -> None:
        """
        Register a resource provider.
        
        Args:
            provider: Resource provider to register
        """
        resource_type = provider.get_resource_type()
        self.providers[resource_type] = provider
        logger.debug(f"Registered resource provider for {resource_type}")

    def get_provider(self, resource_type: ResourceType) -> Optional[ResourceProvider]:
        """
        Get a registered resource provider by type.
        
        Args:
            resource_type: Resource type
            
        Returns:
            Resource provider, or None if not found
        """
        return self.providers.get(resource_type)

    def has_provider(self, resource_type: ResourceType) -> bool:
        """
        Check if a provider is registered for a resource type.
        
        Args:
            resource_type: Resource type
            
        Returns:
            True if a provider is registered, False otherwise
        """
        return resource_type in self.providers

    def get_all_providers(self) -> List[ResourceProvider]:
        """
        Get all registered resource providers.
        
        Returns:
            List of all resource providers
        """
        return list(self.providers.values())
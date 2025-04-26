"""
Access control module.

This module provides functionality for controlling access to resources and methods.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from src.utils.errors import UnauthorizedError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class Permission(str, Enum):
    """Permission levels for resources and methods."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class Role(str, Enum):
    """User roles for access control."""

    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"


class ResourceAccess(BaseModel):
    """Access control for a specific resource."""

    resource: str
    permissions: Set[Permission]


class MethodAccess(BaseModel):
    """Access control for a specific method."""

    method: str
    required_permissions: Set[Permission]


class AccessPolicy(BaseModel):
    """Access control policy for a role."""

    role: Role
    resource_access: Dict[str, Set[Permission]] = Field(default_factory=dict)
    method_access: Dict[str, Set[Permission]] = Field(default_factory=dict)


class AccessControl:
    """
    Access control manager.
    
    This class provides functionality for controlling access to resources and methods
    based on user roles and permissions.
    """

    def __init__(self):
        """Initialize the access control manager."""
        self.policies: Dict[Role, AccessPolicy] = {}
        
        # Set up default policies
        self._setup_default_policies()
        
        logger.info("Access control manager initialized")

    def _setup_default_policies(self) -> None:
        """Set up default access policies."""
        # Guest role has very limited access
        guest_policy = AccessPolicy(
            role=Role.GUEST,
            resource_access={
                "linear.public": {Permission.READ},
            },
            method_access={
                "linear.search": {Permission.READ},
            },
        )
        
        # User role has standard access
        user_policy = AccessPolicy(
            role=Role.USER,
            resource_access={
                "linear.issue": {Permission.READ, Permission.WRITE},
                "linear.project": {Permission.READ},
                "linear.team": {Permission.READ},
                "linear.user": {Permission.READ},
                "linear.comment": {Permission.READ, Permission.WRITE},
            },
            method_access={
                "linear.search": {Permission.READ},
                "linear.convertFeatureList": {Permission.WRITE},
            },
        )
        
        # Admin role has full access
        admin_policy = AccessPolicy(
            role=Role.ADMIN,
            resource_access={
                "linear.issue": {Permission.READ, Permission.WRITE, Permission.ADMIN},
                "linear.project": {Permission.READ, Permission.WRITE, Permission.ADMIN},
                "linear.team": {Permission.READ, Permission.WRITE, Permission.ADMIN},
                "linear.user": {Permission.READ, Permission.WRITE, Permission.ADMIN},
                "linear.comment": {Permission.READ, Permission.WRITE, Permission.ADMIN},
                "linear.label": {Permission.READ, Permission.WRITE, Permission.ADMIN},
                "linear.workflow": {Permission.READ, Permission.WRITE, Permission.ADMIN},
            },
            method_access={
                "linear.search": {Permission.READ, Permission.ADMIN},
                "linear.convertFeatureList": {Permission.WRITE, Permission.ADMIN},
                "linear.admin.config": {Permission.ADMIN},
            },
        )
        
        # Register policies
        self.policies[Role.GUEST] = guest_policy
        self.policies[Role.USER] = user_policy
        self.policies[Role.ADMIN] = admin_policy

    def get_policy(self, role: Role) -> Optional[AccessPolicy]:
        """
        Get the access policy for a role.
        
        Args:
            role: User role
            
        Returns:
            Access policy for the role, or None if not found
        """
        return self.policies.get(role)

    def check_resource_permission(
        self, role: Role, resource: str, permission: Permission
    ) -> bool:
        """
        Check if a role has permission to access a resource.
        
        Args:
            role: User role
            resource: Resource identifier
            permission: Required permission
            
        Returns:
            True if the role has the required permission, False otherwise
        """
        policy = self.get_policy(role)
        if not policy:
            return False
        
        # Admin role has all permissions
        if role == Role.ADMIN:
            return True
        
        # Check resource permissions
        resource_permissions = policy.resource_access.get(resource, set())
        return permission in resource_permissions

    def check_method_permission(
        self, role: Role, method: str, permission: Permission
    ) -> bool:
        """
        Check if a role has permission to execute a method.
        
        Args:
            role: User role
            method: Method name
            permission: Required permission
            
        Returns:
            True if the role has the required permission, False otherwise
        """
        policy = self.get_policy(role)
        if not policy:
            return False
        
        # Admin role has all permissions
        if role == Role.ADMIN:
            return True
        
        # Check method permissions
        method_permissions = policy.method_access.get(method, set())
        return permission in method_permissions

    def require_resource_permission(
        self, role: Role, resource: str, permission: Permission
    ) -> None:
        """
        Require a permission for a resource, raising an error if not allowed.
        
        Args:
            role: User role
            resource: Resource identifier
            permission: Required permission
            
        Raises:
            UnauthorizedError: If the role does not have the required permission
        """
        if not self.check_resource_permission(role, resource, permission):
            logger.warning(
                f"Permission denied for role {role} on resource {resource} "
                f"(required: {permission})"
            )
            raise UnauthorizedError(
                f"Permission denied: {permission} access required for {resource}"
            )

    def require_method_permission(
        self, role: Role, method: str, permission: Permission
    ) -> None:
        """
        Require a permission for a method, raising an error if not allowed.
        
        Args:
            role: User role
            method: Method name
            permission: Required permission
            
        Raises:
            UnauthorizedError: If the role does not have the required permission
        """
        if not self.check_method_permission(role, method, permission):
            logger.warning(
                f"Permission denied for role {role} on method {method} "
                f"(required: {permission})"
            )
            raise UnauthorizedError(
                f"Permission denied: {permission} access required for {method}"
            )


def get_access_control() -> AccessControl:
    """
    Get the global access control instance.
    
    Returns:
        Access control instance
    """
    # Singleton pattern
    if not hasattr(get_access_control, "_instance"):
        get_access_control._instance = AccessControl()
    
    return get_access_control._instance
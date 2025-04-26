"""
MCP protocol version negotiation module.

This module provides functionality for handling MCP protocol version compatibility.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MCPVersion(str, Enum):
    """MCP protocol version enumeration."""

    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class VersionRange(BaseModel):
    """
    Model representing a range of protocol versions.
    
    This model supports a range with inclusive minimum and maximum versions.
    """

    min_version: MCPVersion
    max_version: Optional[MCPVersion] = None

    def contains(self, version: MCPVersion) -> bool:
        """
        Check if a version is within this range.
        
        Args:
            version: Version to check
            
        Returns:
            True if the version is within this range, False otherwise
        """
        if self.max_version is None:
            # If no max version, any version >= min_version is valid
            return version.value >= self.min_version.value
        
        # Otherwise, must be between min and max (inclusive)
        return (
            version.value >= self.min_version.value
            and version.value <= self.max_version.value
        )


class VersionNegotiator:
    """
    Negotiator for MCP protocol version compatibility.
    
    This class handles protocol version negotiation between client and server.
    """

    def __init__(self, supported_versions: List[MCPVersion]):
        """
        Initialize the version negotiator.
        
        Args:
            supported_versions: List of versions supported by the server
        """
        self.supported_versions = supported_versions
        # Sort versions by value
        self.supported_versions.sort(key=lambda v: v.value)
        self.latest_version = self.supported_versions[-1] if self.supported_versions else None
        logger.info(f"MCP version negotiator initialized with versions: {self.supported_versions}")

    def get_compatible_version(
        self, client_versions: List[MCPVersion]
    ) -> Optional[MCPVersion]:
        """
        Find the highest compatible version between client and server.
        
        Args:
            client_versions: List of versions supported by the client
            
        Returns:
            Highest compatible version, or None if no compatible version found
        """
        # Convert to sets for efficient intersection
        server_set = set(self.supported_versions)
        client_set = set(client_versions)
        
        # Find common versions
        common_versions = list(server_set.intersection(client_set))
        
        if not common_versions:
            logger.warning(
                f"No compatible versions found. Server supports {self.supported_versions}, "
                f"client supports {client_versions}"
            )
            return None
        
        # Sort by version to find highest
        common_versions.sort(key=lambda v: v.value)
        highest_version = common_versions[-1]
        
        logger.info(f"Negotiated compatible version: {highest_version}")
        return highest_version

    def get_compatible_version_from_range(
        self, version_range: VersionRange
    ) -> Optional[MCPVersion]:
        """
        Find the highest compatible version between the server and a client version range.
        
        Args:
            version_range: Range of versions supported by the client
            
        Returns:
            Highest compatible version, or None if no compatible version found
        """
        # Find all server versions that are within the client's range
        compatible_versions = [
            version for version in self.supported_versions 
            if version_range.contains(version)
        ]
        
        if not compatible_versions:
            logger.warning(
                f"No compatible versions found. Server supports {self.supported_versions}, "
                f"client supports range {version_range}"
            )
            return None
        
        # Return the highest compatible version
        highest_version = compatible_versions[-1]
        logger.info(f"Negotiated compatible version from range: {highest_version}")
        return highest_version

    def is_version_supported(self, version: MCPVersion) -> bool:
        """
        Check if a specific version is supported by the server.
        
        Args:
            version: Version to check
            
        Returns:
            True if the version is supported, False otherwise
        """
        return version in self.supported_versions

    def get_supported_version_range(self) -> VersionRange:
        """
        Get the range of versions supported by the server.
        
        Returns:
            Version range representing the server's supported versions
        """
        if not self.supported_versions:
            # Default to a single version if none specified
            return VersionRange(min_version=MCPVersion.V1_0, max_version=MCPVersion.V1_0)
        
        return VersionRange(
            min_version=self.supported_versions[0],
            max_version=self.supported_versions[-1],
        )


class FeatureVersionMap:
    """
    Map of features to the MCP versions that support them.
    
    This class helps determine which features are available in a specific protocol version.
    """

    def __init__(self):
        """Initialize the feature version map."""
        self.feature_map: Dict[str, VersionRange] = {}

    def add_feature(self, feature: str, version_range: VersionRange) -> None:
        """
        Add a feature to the map.
        
        Args:
            feature: Feature name
            version_range: Range of versions that support the feature
        """
        self.feature_map[feature] = version_range

    def is_feature_supported(self, feature: str, version: MCPVersion) -> bool:
        """
        Check if a feature is supported in a specific version.
        
        Args:
            feature: Feature name
            version: Protocol version
            
        Returns:
            True if the feature is supported, False otherwise
        """
        if feature not in self.feature_map:
            return False
        
        return self.feature_map[feature].contains(version)

    def get_supported_features(self, version: MCPVersion) -> List[str]:
        """
        Get a list of features supported in a specific version.
        
        Args:
            version: Protocol version
            
        Returns:
            List of supported features
        """
        return [
            feature
            for feature, version_range in self.feature_map.items()
            if version_range.contains(version)
        ]
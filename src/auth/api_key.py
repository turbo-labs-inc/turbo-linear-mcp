"""
API key validation module.

This module provides functionality for validating Linear API keys.
"""

import re
from typing import Dict, Optional, Union

import requests

from src.utils.errors import UnauthorizedError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ApiKeyValidator:
    """
    Validator for Linear API keys.
    
    This class provides functionality for validating and caching Linear API keys.
    """

    def __init__(self):
        """Initialize the API key validator."""
        self.api_key_cache: Dict[str, bool] = {}
        self.api_url = "https://api.linear.app/graphql"
        
        # Linear API keys typically start with "lin_"
        self.api_key_pattern = re.compile(r"^lin_[a-zA-Z0-9]{40,}$")
        
        logger.info("API key validator initialized")

    def validate_format(self, api_key: str) -> bool:
        """
        Validate that an API key has the correct format.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if the format is valid, False otherwise
        """
        return bool(self.api_key_pattern.match(api_key))

    async def validate_with_api(self, api_key: str) -> bool:
        """
        Validate an API key by making a test request to the Linear API.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if the API key is valid, False otherwise
        """
        if api_key in self.api_key_cache:
            return self.api_key_cache[api_key]
        
        # Simple viewer query to test the API key
        query = """
        query {
          viewer {
            id
            name
          }
        }
        """
        
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.post(
                self.api_url,
                json={"query": query},
                headers=headers,
                timeout=5,
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "viewer" in data["data"]:
                    # Cache the result
                    self.api_key_cache[api_key] = True
                    logger.info("API key validation successful")
                    return True
            
            # Invalid API key
            logger.warning(f"API key validation failed: HTTP {response.status_code}")
            self.api_key_cache[api_key] = False
            return False
        
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False

    async def validate(self, api_key: str) -> bool:
        """
        Validate an API key using both format and API checks.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if the API key is valid, False otherwise
        """
        # First check format
        if not self.validate_format(api_key):
            logger.warning("API key has invalid format")
            return False
        
        # Then check with API
        return await self.validate_with_api(api_key)


def get_api_key_validator() -> ApiKeyValidator:
    """
    Get the global API key validator instance.
    
    Returns:
        API key validator instance
    """
    # Singleton pattern
    if not hasattr(get_api_key_validator, "_instance"):
        get_api_key_validator._instance = ApiKeyValidator()
    
    return get_api_key_validator._instance


async def validate_api_key(api_key: str) -> None:
    """
    Validate an API key and raise an error if invalid.
    
    Args:
        api_key: API key to validate
        
    Raises:
        UnauthorizedError: If the API key is invalid
    """
    validator = get_api_key_validator()
    
    if not await validator.validate(api_key):
        logger.warning("Invalid API key provided")
        raise UnauthorizedError("Invalid Linear API key")
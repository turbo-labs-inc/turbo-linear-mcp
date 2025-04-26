"""
Input validation utilities.

This module provides utilities for validating user input to prevent security issues.
"""

import re
from typing import Any, Dict, List, Optional, Type, Union

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, validator

from src.utils.errors import ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class InputValidator:
    """
    Validator for user input.
    
    This class provides methods for validating and sanitizing user input
    to prevent security issues like injection attacks.
    """

    # Common patterns for validation
    PATTERNS = {
        "alphanumeric": re.compile(r"^[a-zA-Z0-9_]+$"),
        "email": re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
        "url": re.compile(
            r"^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}"
            r"\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
        ),
        "linear_id": re.compile(r"^[a-zA-Z0-9-]+$"),
    }

    @staticmethod
    def validate_string(value: str, pattern_name: str) -> bool:
        """
        Validate a string against a named pattern.
        
        Args:
            value: String to validate
            pattern_name: Name of the pattern to use
            
        Returns:
            True if the string matches the pattern, False otherwise
        """
        if pattern_name not in InputValidator.PATTERNS:
            logger.error(f"Unknown pattern: {pattern_name}")
            return False
        
        pattern = InputValidator.PATTERNS[pattern_name]
        return bool(pattern.match(value))

    @staticmethod
    def sanitize_string(value: str) -> str:
        """
        Sanitize a string to prevent injection attacks.
        
        Args:
            value: String to sanitize
            
        Returns:
            Sanitized string
        """
        # Remove any control characters
        sanitized = "".join(
            c for c in value if c.isprintable() and c not in "<>&'\";"
        )
        return sanitized

    @staticmethod
    def validate_linear_id(value: str) -> bool:
        """
        Validate a Linear ID.
        
        Args:
            value: ID to validate
            
        Returns:
            True if the ID is valid, False otherwise
        """
        return InputValidator.validate_string(value, "linear_id")

    @staticmethod
    def validate_email(value: str) -> bool:
        """
        Validate an email address.
        
        Args:
            value: Email to validate
            
        Returns:
            True if the email is valid, False otherwise
        """
        return InputValidator.validate_string(value, "email")

    @staticmethod
    def validate_url(value: str) -> bool:
        """
        Validate a URL.
        
        Args:
            value: URL to validate
            
        Returns:
            True if the URL is valid, False otherwise
        """
        return InputValidator.validate_string(value, "url")

    @staticmethod
    def validate_dictionary(
        data: Dict[str, Any], required_keys: List[str], allowed_keys: Optional[List[str]] = None
    ) -> bool:
        """
        Validate a dictionary.
        
        Args:
            data: Dictionary to validate
            required_keys: Keys that must be present
            allowed_keys: Optional list of all allowed keys
            
        Returns:
            True if the dictionary is valid, False otherwise
        """
        # Check required keys
        for key in required_keys:
            if key not in data:
                logger.warning(f"Missing required key: {key}")
                return False
        
        # Check allowed keys if specified
        if allowed_keys is not None:
            for key in data:
                if key not in allowed_keys:
                    logger.warning(f"Unexpected key: {key}")
                    return False
        
        return True

    @staticmethod
    def validate_model(data: Dict[str, Any], model_class: Type[BaseModel]) -> Optional[BaseModel]:
        """
        Validate data using a Pydantic model.
        
        Args:
            data: Data to validate
            model_class: Pydantic model class
            
        Returns:
            Validated model instance, or None if validation fails
        """
        try:
            return model_class(**data)
        except Exception as e:
            logger.warning(f"Model validation failed: {e}")
            return None


class SearchQuery(BaseModel):
    """Model for validating search queries."""

    query: str = Field(..., min_length=1, max_length=1000)
    resource_types: Optional[List[str]] = None
    limit: Optional[int] = Field(None, ge=1, le=100)
    offset: Optional[int] = Field(None, ge=0)
    
    @validator("query")
    def validate_query(cls, v: str) -> str:
        """Validate and sanitize search query."""
        return InputValidator.sanitize_string(v)
    
    @validator("resource_types")
    def validate_resource_types(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate resource types."""
        if v is None:
            return None
        
        valid_types = ["issue", "project", "team", "user", "comment"]
        for rt in v:
            if rt not in valid_types:
                raise ValueError(f"Invalid resource type: {rt}")
        
        return v


class FeatureListInput(BaseModel):
    """Model for validating feature list input."""

    text: str = Field(..., min_length=1, max_length=50000)
    format: str = Field("text", pattern="^(text|markdown|json)$")
    team_id: Optional[str] = None
    project_id: Optional[str] = None
    labels: Optional[List[str]] = None
    
    @validator("text")
    def validate_text(cls, v: str) -> str:
        """Validate and sanitize feature list text."""
        # For feature lists, we don't want to sanitize too much
        # but we should still remove any control characters
        return "".join(c for c in v if c.isprintable())
    
    @validator("team_id", "project_id")
    def validate_ids(cls, v: Optional[str]) -> Optional[str]:
        """Validate Linear IDs."""
        if v is None:
            return None
        
        if not InputValidator.validate_linear_id(v):
            raise ValueError(f"Invalid Linear ID format: {v}")
        
        return v


def validate_search_query(query_data: Dict[str, Any]) -> SearchQuery:
    """
    Validate a search query.
    
    Args:
        query_data: Search query data
        
    Returns:
        Validated search query model
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        return SearchQuery(**query_data)
    except Exception as e:
        logger.warning(f"Search query validation failed: {e}")
        raise ValidationError(f"Invalid search query: {e}")


def validate_feature_list(feature_list_data: Dict[str, Any]) -> FeatureListInput:
    """
    Validate a feature list input.
    
    Args:
        feature_list_data: Feature list data
        
    Returns:
        Validated feature list model
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        return FeatureListInput(**feature_list_data)
    except Exception as e:
        logger.warning(f"Feature list validation failed: {e}")
        raise ValidationError(f"Invalid feature list: {e}")
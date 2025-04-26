"""
Environment variable management for the Linear MCP Server.

This module provides utilities for loading and accessing environment variables.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv


def load_env_file(env_file: Optional[Union[str, Path]] = None) -> bool:
    """
    Load environment variables from .env file.

    Args:
        env_file: Path to .env file. If not provided, looks for .env in current
                  directory and parent directories.

    Returns:
        True if environment variables were loaded successfully, False otherwise.
    """
    if env_file:
        return load_dotenv(env_file)
    
    # Try to find .env file in current directory or parent directories
    return load_dotenv(dotenv_path=None, override=True)


def get_env(key: str, default: Any = None) -> str:
    """
    Get an environment variable.

    Args:
        key: Environment variable name
        default: Default value if environment variable is not set

    Returns:
        Environment variable value or default if not set
    """
    return os.getenv(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get a boolean environment variable.

    Args:
        key: Environment variable name
        default: Default value if environment variable is not set

    Returns:
        True if environment variable is "1", "true", "yes", or "y" (case insensitive),
        False otherwise.
    """
    value = get_env(key)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "y")


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get an integer environment variable.

    Args:
        key: Environment variable name
        default: Default value if environment variable is not set or invalid

    Returns:
        Integer value of environment variable or default if not set or invalid
    """
    value = get_env(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """
    Get a float environment variable.

    Args:
        key: Environment variable name
        default: Default value if environment variable is not set or invalid

    Returns:
        Float value of environment variable or default if not set or invalid
    """
    value = get_env(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_env_list(key: str, default: Optional[List[str]] = None, separator: str = ",") -> List[str]:
    """
    Get a list environment variable by splitting a string with the given separator.

    Args:
        key: Environment variable name
        default: Default value if environment variable is not set
        separator: String separator to split the environment variable value

    Returns:
        List of strings from environment variable or default if not set
    """
    value = get_env(key)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(separator) if item.strip()]


def get_env_dict(key: str, default: Optional[Dict[str, str]] = None, item_separator: str = ",", 
                key_value_separator: str = "=") -> Dict[str, str]:
    """
    Get a dictionary environment variable by parsing a string with the given separators.

    Args:
        key: Environment variable name
        default: Default value if environment variable is not set
        item_separator: String separator for dictionary items
        key_value_separator: String separator for keys and values

    Returns:
        Dictionary from environment variable or default if not set
    """
    value = get_env(key)
    if value is None:
        return default or {}
    
    result = {}
    for item in value.split(item_separator):
        if not item.strip():
            continue
        if key_value_separator not in item:
            continue
        k, v = item.split(key_value_separator, 1)
        result[k.strip()] = v.strip()
    
    return result
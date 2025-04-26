"""
Tests for the configuration management module.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.config.config import Config, load_config, load_config_from_env


def test_load_config_valid_file():
    """Test loading a valid configuration file."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+") as temp_file:
        yaml.dump(
            {
                "linear": {
                    "api_key": "test_api_key",
                },
                "server": {
                    "port": 9000,
                },
                "logging": {
                    "level": "DEBUG",
                },
                "debug": True,
            },
            temp_file,
        )
        temp_file.flush()
        
        config = load_config(temp_file.name)
        
        assert isinstance(config, Config)
        assert config.linear.api_key == "test_api_key"
        assert config.server.port == 9000
        assert config.logging.level == "DEBUG"
        assert config.debug is True


def test_load_config_file_not_found():
    """Test error handling when configuration file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config.yaml")


def test_load_config_invalid_yaml():
    """Test error handling for invalid YAML."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+") as temp_file:
        temp_file.write("invalid: yaml: file:")
        temp_file.flush()
        
        with pytest.raises(ValueError):
            load_config(temp_file.name)


def test_load_config_missing_required_field():
    """Test error handling when required field is missing."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+") as temp_file:
        yaml.dump(
            {
                "server": {
                    "port": 9000,
                },
            },
            temp_file,
        )
        temp_file.flush()
        
        with pytest.raises(ValueError):
            load_config(temp_file.name)


def test_load_config_from_env(test_env_vars):
    """Test loading configuration from environment variables."""
    config = load_config_from_env()
    
    assert isinstance(config, Config)
    assert config.linear.api_key == "test_env_api_key"
    assert config.server.port == 9000
    assert config.logging.level == "DEBUG"
    assert config.debug is True
    assert config.environment == "test"


def test_env_config_overrides_file_config():
    """Test that environment variables override file configuration."""
    # TBD: Implement this test when environment-specific config loading is implemented
    pass
"""
Tests for the environment variable management module.
"""

import os
import tempfile

import pytest

from src.utils.environment import (
    get_env,
    get_env_bool,
    get_env_dict,
    get_env_float,
    get_env_int,
    get_env_list,
    load_env_file,
)


def test_load_env_file():
    """Test loading environment variables from .env file."""
    with tempfile.NamedTemporaryFile(suffix=".env", mode="w+") as temp_file:
        temp_file.write("TEST_VAR=test_value\nTEST_INT=42\n")
        temp_file.flush()
        
        assert load_env_file(temp_file.name)
        assert os.getenv("TEST_VAR") == "test_value"
        assert os.getenv("TEST_INT") == "42"


def test_get_env():
    """Test get_env function."""
    os.environ["TEST_GET_ENV"] = "test_value"
    assert get_env("TEST_GET_ENV") == "test_value"
    assert get_env("NONEXISTENT_ENV") is None
    assert get_env("NONEXISTENT_ENV", "default") == "default"


def test_get_env_bool():
    """Test get_env_bool function."""
    test_cases = {
        "TRUE_VAR_1": "true",
        "TRUE_VAR_2": "TRUE",
        "TRUE_VAR_3": "yes",
        "TRUE_VAR_4": "y",
        "TRUE_VAR_5": "1",
        "FALSE_VAR_1": "false",
        "FALSE_VAR_2": "no",
        "FALSE_VAR_3": "n",
        "FALSE_VAR_4": "0",
        "FALSE_VAR_5": "anything else",
    }
    
    for var, value in test_cases.items():
        os.environ[var] = value
    
    assert get_env_bool("TRUE_VAR_1") is True
    assert get_env_bool("TRUE_VAR_2") is True
    assert get_env_bool("TRUE_VAR_3") is True
    assert get_env_bool("TRUE_VAR_4") is True
    assert get_env_bool("TRUE_VAR_5") is True
    
    assert get_env_bool("FALSE_VAR_1") is False
    assert get_env_bool("FALSE_VAR_2") is False
    assert get_env_bool("FALSE_VAR_3") is False
    assert get_env_bool("FALSE_VAR_4") is False
    assert get_env_bool("FALSE_VAR_5") is False
    
    assert get_env_bool("NONEXISTENT_ENV") is False
    assert get_env_bool("NONEXISTENT_ENV", True) is True


def test_get_env_int():
    """Test get_env_int function."""
    os.environ["INT_VAR"] = "42"
    os.environ["FLOAT_VAR"] = "3.14"
    os.environ["STRING_VAR"] = "not a number"
    
    assert get_env_int("INT_VAR") == 42
    assert get_env_int("FLOAT_VAR") == 3  # Integer conversion truncates
    assert get_env_int("STRING_VAR") == 0  # Default for invalid conversion
    assert get_env_int("STRING_VAR", -1) == -1  # Custom default
    assert get_env_int("NONEXISTENT_ENV") == 0
    assert get_env_int("NONEXISTENT_ENV", 100) == 100


def test_get_env_float():
    """Test get_env_float function."""
    os.environ["INT_VAR"] = "42"
    os.environ["FLOAT_VAR"] = "3.14"
    os.environ["STRING_VAR"] = "not a number"
    
    assert get_env_float("INT_VAR") == 42.0
    assert get_env_float("FLOAT_VAR") == 3.14
    assert get_env_float("STRING_VAR") == 0.0  # Default for invalid conversion
    assert get_env_float("STRING_VAR", -1.5) == -1.5  # Custom default
    assert get_env_float("NONEXISTENT_ENV") == 0.0
    assert get_env_float("NONEXISTENT_ENV", 100.5) == 100.5


def test_get_env_list():
    """Test get_env_list function."""
    os.environ["LIST_VAR"] = "a,b,c"
    os.environ["LIST_VAR_SPACES"] = " a, b ,c "
    os.environ["LIST_VAR_EMPTY"] = ""
    os.environ["LIST_VAR_CUSTOM_SEP"] = "a|b|c"
    
    assert get_env_list("LIST_VAR") == ["a", "b", "c"]
    assert get_env_list("LIST_VAR_SPACES") == ["a", "b", "c"]
    assert get_env_list("LIST_VAR_EMPTY") == []
    assert get_env_list("LIST_VAR_CUSTOM_SEP", separator="|") == ["a", "b", "c"]
    assert get_env_list("NONEXISTENT_ENV") == []
    assert get_env_list("NONEXISTENT_ENV", ["default"]) == ["default"]


def test_get_env_dict():
    """Test get_env_dict function."""
    os.environ["DICT_VAR"] = "a=1,b=2,c=3"
    os.environ["DICT_VAR_SPACES"] = " a = 1, b = 2 ,c= 3 "
    os.environ["DICT_VAR_EMPTY"] = ""
    os.environ["DICT_VAR_INVALID"] = "a=1,invalid,b=2"
    os.environ["DICT_VAR_CUSTOM_SEP"] = "a=1|b=2|c=3"
    
    assert get_env_dict("DICT_VAR") == {"a": "1", "b": "2", "c": "3"}
    assert get_env_dict("DICT_VAR_SPACES") == {"a": "1", "b": "2", "c": "3"}
    assert get_env_dict("DICT_VAR_EMPTY") == {}
    assert get_env_dict("DICT_VAR_INVALID") == {"a": "1", "b": "2"}
    assert get_env_dict("DICT_VAR_CUSTOM_SEP", item_separator="|") == {"a": "1", "b": "2", "c": "3"}
    assert get_env_dict("NONEXISTENT_ENV") == {}
    assert get_env_dict("NONEXISTENT_ENV", {"default": "value"}) == {"default": "value"}
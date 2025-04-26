"""
Tests for the API key validation module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.auth.api_key import ApiKeyValidator, validate_api_key
from src.utils.errors import UnauthorizedError


def test_api_key_validator_init():
    """Test initializing the API key validator."""
    validator = ApiKeyValidator()
    assert validator.api_key_cache == {}
    assert validator.api_url == "https://api.linear.app/graphql"
    assert validator.api_key_pattern is not None


def test_validate_format_valid():
    """Test validating a valid API key format."""
    validator = ApiKeyValidator()
    valid_key = "lin_api_12345abcdef67890abcdef12345abcdef67890abcdef"
    assert validator.validate_format(valid_key)


def test_validate_format_invalid():
    """Test validating an invalid API key format."""
    validator = ApiKeyValidator()
    invalid_keys = [
        "invalid_key",
        "lin_12345",
        "lin@api_12345abcdef",
        "",
        "lin_api",
    ]
    
    for key in invalid_keys:
        assert not validator.validate_format(key)


@pytest.mark.asyncio
async def test_validate_with_api_success():
    """Test successful API key validation with Linear API."""
    validator = ApiKeyValidator()
    
    # Mock requests.post
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "viewer": {
                    "id": "user123",
                    "name": "Test User",
                }
            }
        }
        mock_post.return_value = mock_response
        
        # Test validation
        valid_key = "lin_api_12345abcdef67890abcdef12345abcdef67890abcdef"
        result = await validator.validate_with_api(valid_key)
        
        assert result is True
        assert valid_key in validator.api_key_cache
        assert validator.api_key_cache[valid_key] is True
        
        # Check that the request was made with the correct parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == validator.api_url
        assert kwargs["headers"]["Authorization"] == valid_key
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert "query" in kwargs["json"]


@pytest.mark.asyncio
async def test_validate_with_api_failure():
    """Test failed API key validation with Linear API."""
    validator = ApiKeyValidator()
    
    # Mock requests.post
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "errors": [
                {
                    "message": "Not authenticated",
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Test validation
        invalid_key = "lin_api_invalid"
        result = await validator.validate_with_api(invalid_key)
        
        assert result is False
        assert invalid_key in validator.api_key_cache
        assert validator.api_key_cache[invalid_key] is False


@pytest.mark.asyncio
async def test_validate_with_api_exception():
    """Test API key validation with exception."""
    validator = ApiKeyValidator()
    
    # Mock requests.post to raise an exception
    with patch("requests.post") as mock_post:
        mock_post.side_effect = Exception("Connection error")
        
        # Test validation
        key = "lin_api_12345abcdef67890abcdef12345abcdef67890abcdef"
        result = await validator.validate_with_api(key)
        
        assert result is False
        assert key not in validator.api_key_cache


@pytest.mark.asyncio
async def test_validate_from_cache():
    """Test validating an API key from cache."""
    validator = ApiKeyValidator()
    key = "lin_api_12345abcdef67890abcdef12345abcdef67890abcdef"
    
    # Add key to cache
    validator.api_key_cache[key] = True
    
    # Mock validate_with_api to ensure it's not called
    validator.validate_with_api = AsyncMock()
    
    # Test validation
    result = await validator.validate_with_api(key)
    
    assert result is True
    validator.validate_with_api.assert_not_called()


@pytest.mark.asyncio
async def test_validate():
    """Test the main validate method."""
    validator = ApiKeyValidator()
    key = "lin_api_12345abcdef67890abcdef12345abcdef67890abcdef"
    
    # Mock validate_format and validate_with_api
    validator.validate_format = MagicMock(return_value=True)
    validator.validate_with_api = AsyncMock(return_value=True)
    
    # Test validation
    result = await validator.validate(key)
    
    assert result is True
    validator.validate_format.assert_called_once_with(key)
    validator.validate_with_api.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_validate_invalid_format():
    """Test validation with invalid format."""
    validator = ApiKeyValidator()
    key = "invalid_key"
    
    # Mock validate_format and validate_with_api
    validator.validate_format = MagicMock(return_value=False)
    validator.validate_with_api = AsyncMock()
    
    # Test validation
    result = await validator.validate(key)
    
    assert result is False
    validator.validate_format.assert_called_once_with(key)
    validator.validate_with_api.assert_not_called()


@pytest.mark.asyncio
async def test_validate_api_key_function():
    """Test the validate_api_key function."""
    key = "lin_api_12345abcdef67890abcdef12345abcdef67890abcdef"
    
    # Mock get_api_key_validator
    mock_validator = MagicMock()
    mock_validator.validate = AsyncMock(return_value=True)
    
    with patch("src.auth.api_key.get_api_key_validator", return_value=mock_validator):
        # Test successful validation
        await validate_api_key(key)
        mock_validator.validate.assert_called_once_with(key)
        
        # Test failed validation
        mock_validator.validate.reset_mock()
        mock_validator.validate.return_value = False
        
        with pytest.raises(UnauthorizedError):
            await validate_api_key(key)
        mock_validator.validate.assert_called_once_with(key)
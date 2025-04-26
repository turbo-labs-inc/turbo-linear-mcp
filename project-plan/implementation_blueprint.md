# Implementation Blueprint for Linear MCP Server

## Overview
This document provides a comprehensive implementation blueprint for the Linear MCP server. It outlines the project structure, key components, implementation sequence, and technical considerations to guide the development process.

## Project Structure

```
linear-mcp-server/
├── config/
│   ├── default.yaml       # Default configuration
│   └── production.yaml    # Production overrides
├── src/
│   ├── main.py            # Application entry point
│   ├── config.py          # Configuration loading and validation
│   ├── server.py          # MCP server implementation
│   ├── mcp/               # MCP protocol implementation
│   │   ├── __init__.py
│   │   ├── connection.py  # Connection management
│   │   ├── message.py     # Message handling
│   │   ├── resources.py   # Resource implementations
│   │   ├── tools.py       # Tool implementations
│   │   └── protocol.py    # Protocol utilities
│   ├── linear/            # Linear API integration
│   │   ├── __init__.py
│   │   ├── client.py      # API client
│   │   ├── auth.py        # Authentication
│   │   ├── feature_list.py # Feature list processing
│   │   ├── search.py      # Search implementation
│   │   └── models.py      # Data models
│   ├── utils/             # Utility modules
│   │   ├── __init__.py
│   │   ├── logging.py     # Logging utilities
│   │   ├── errors.py      # Error handling
│   │   └── security.py    # Security utilities
│   └── api/               # API endpoints (if needed)
│       ├── __init__.py
│       ├── routes.py      # Route definitions
│       └── handlers.py    # Request handlers
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── conftest.py        # Test configuration
│   ├── test_mcp/          # MCP protocol tests
│   ├── test_linear/       # Linear API tests
│   └── test_integration/  # Integration tests
├── scripts/               # Utility scripts
│   ├── setup.sh           # Setup script
│   └── deploy.sh          # Deployment script
├── docs/                  # Documentation
│   ├── api.md             # API documentation
│   ├── configuration.md   # Configuration guide
│   └── usage.md           # Usage guide
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
└── README.md              # Project overview
```

## Key Components Implementation

### 1. Configuration Management

```python
# src/config.py
import os
import yaml
from typing import Any, Dict, Optional

class Config:
    """Configuration manager for the Linear MCP server."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration from file and environment variables."""
        self.config = self._load_default_config()
        
        if config_path:
            self._load_from_file(config_path)
        
        self._override_from_env()
        self._validate()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration values."""
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 8080,
                "max_connections": 100,
                "connection_timeout": 30,
                "request_timeout": 60,
                "debug": False
            },
            "mcp": {
                "version": "2025-03-26",
                "capabilities": {
                    "resources": True,
                    "tools": True,
                    "prompts": False,
                    "sampling": False
                },
                "resources": {
                    "max_per_page": 50,
                    "cache_enabled": True,
                    "cache_ttl": 300
                },
                "tools": {
                    "max_execution_time": 120,
                    "rate_limit": {
                        "enabled": True,
                        "max_per_minute": 60
                    }
                }
            },
            "linear": {
                "api_url": "https://api.linear.app/graphql",
                "auth": {
                    "method": "api_key",
                    "api_key": ""
                },
                "rate_limit": {
                    "max_retries": 3,
                    "retry_delay": 1000,
                    "exponential_backoff": True
                },
                "feature_list": {
                    "max_batch_size": 50,
                    "parsing": {
                        "markdown_support": True,
                        "json_support": True,
                        "extract_metadata": True
                    }
                },
                "search": {
                    "max_results_per_page": 25,
                    "cache_results": True,
                    "cache_ttl": 60
                }
            },
            "logging": {
                "level": "info",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "",
                "max_size": 10,
                "backup_count": 5,
                "log_requests": True,
                "log_api_calls": True
            },
            "security": {
                "ssl": {
                    "enabled": False,
                    "cert_file": "",
                    "key_file": ""
                },
                "cors": {
                    "enabled": True,
                    "allowed_origins": ["*"],
                    "allowed_methods": ["GET", "POST"],
                    "allowed_headers": ["Content-Type", "Authorization"]
                },
                "api_key": ""
            }
        }
    
    def _load_from_file(self, config_path: str) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                self._merge_config(file_config)
        except Exception as e:
            raise ConfigError(f"Failed to load configuration from {config_path}: {str(e)}")
    
    def _override_from_env(self) -> None:
        """Override configuration with environment variables."""
        env_mappings = {
            "LINEAR_MCP_SERVER_HOST": "server.host",
            "LINEAR_MCP_SERVER_PORT": "server.port",
            "LINEAR_API_KEY": "linear.auth.api_key",
            "LINEAR_OAUTH_CLIENT_ID": "linear.auth.oauth.client_id",
            "LINEAR_OAUTH_CLIENT_SECRET": "linear.auth.oauth.client_secret",
            "LINEAR_MCP_API_KEY": "security.api_key",
            "LINEAR_MCP_LOG_LEVEL": "logging.level",
            "LINEAR_MCP_LOG_FILE": "logging.file"
        }
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                self._set_config_value(config_path, os.environ[env_var])
    
    def _merge_config(self, config: Dict[str, Any], base: Optional[Dict[str, Any]] = None, path: str = "") -> None:
        """Recursively merge configuration dictionaries."""
        if base is None:
            base = self.config
        
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_config(value, base[key], current_path)
            else:
                base[key] = value
    
    def _set_config_value(self, path: str, value: Any) -> None:
        """Set a configuration value at the specified path."""
        parts = path.split('.')
        config = self.config
        
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
        
        config[parts[-1]] = value
    
    def _validate(self) -> None:
        """Validate the configuration."""
        # Validate required fields
        if self.get("linear.auth.method") == "api_key" and not self.get("linear.auth.api_key"):
            raise ConfigError("Linear API key is required when using api_key authentication method")
        
        if self.get("linear.auth.method") == "oauth":
            if not self.get("linear.auth.oauth.client_id"):
                raise ConfigError("OAuth client ID is required when using oauth authentication method")
            if not self.get("linear.auth.oauth.client_secret"):
                raise ConfigError("OAuth client secret is required when using oauth authentication method")
            if not self.get("linear.auth.oauth.redirect_uri"):
                raise ConfigError("OAuth redirect URI is required when using oauth authentication method")
        
        # Validate value ranges
        if not (0 < self.get("server.port", 0) < 65536):
            raise ConfigError("Server port must be between 1 and 65535")
        
        if self.get("server.max_connections", 0) < 1:
            raise ConfigError("Maximum connections must be at least 1")
        
        # Validate SSL configuration
        if self.get("security.ssl.enabled"):
            if not self.get("security.ssl.cert_file"):
                raise ConfigError("SSL certificate file is required when SSL is enabled")
            if not self.get("security.ssl.key_file"):
                raise ConfigError("SSL key file is required when SSL is enabled")
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get a configuration value at the specified path."""
        parts = path.split('.')
        config = self.config
        
        for part in parts:
            if part not in config:
                return default
            config = config[part]
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Return the entire configuration as a dictionary."""
        return self.config.copy()


class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass
```

### 2. MCP Protocol Implementation

```python
# src/mcp/message.py
import json
from typing import Any, Dict, List, Optional, Union

class McpMessage:
    """MCP protocol message handler."""
    
    @staticmethod
    def parse(data: str) -> Dict[str, Any]:
        """Parse a JSON-RPC message string."""
        try:
            message = json.loads(data)
            return message
        except json.JSONDecodeError as e:
            raise McpProtocolError(
                message="Invalid JSON in message",
                details={"error": str(e)}
            )
    
    @staticmethod
    def validate_request(message: Dict[str, Any]) -> None:
        """Validate a JSON-RPC request message."""
        if not isinstance(message, dict):
            raise McpProtocolError(
                message="Invalid message format: must be a JSON object",
                details={"received_type": type(message).__name__}
            )
        
        # Validate required fields
        if "jsonrpc" not in message:
            raise McpProtocolError(
                message="Missing required field: jsonrpc",
                details={"received_message": message}
            )
        
        if message["jsonrpc"] != "2.0":
            raise McpProtocolError(
                message="Unsupported JSON-RPC version",
                details={"received_version": message["jsonrpc"]}
            )
        
        if "method" not in message:
            raise McpProtocolError(
                message="Missing required field: method",
                details={"received_message": message}
            )
        
        if "id" not in message:
            raise McpProtocolError(
                message="Missing required field: id",
                details={"received_message": message}
            )
        
        # Validate params if present
        if "params" in message and not isinstance(message["params"], (dict, list)):
            raise McpProtocolError(
                message="Invalid params: must be an object or array",
                details={"received_params_type": type(message["params"]).__name__}
            )
    
    @staticmethod
    def create_response(id: Union[str, int], result: Any) -> Dict[str, Any]:
        """Create a JSON-RPC response message."""
        return {
            "jsonrpc": "2.0",
            "id": id,
            "result": result
        }
    
    @staticmethod
    def create_error_response(id: Union[str, int, None], code: int, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a JSON-RPC error response message."""
        error = {
            "code": code,
            "message": message
        }
        
        if data:
            error["data"] = data
        
        return {
            "jsonrpc": "2.0",
            "id": id,
            "error": error
        }
    
    @staticmethod
    def create_notification(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a JSON-RPC notification message (no id)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        
        if params:
            notification["params"] = params
        
        return notification


class McpProtocolError(Exception):
    """Exception raised for MCP protocol errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)
```

### 3. Linear API Client

```python
# src/linear/client.py
import aiohttp
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

from .auth import ApiKeyAuthenticator, OAuthAuthenticator
from ..utils.errors import LinearApiError, RateLimitError

class LinearClient:
    """Client for interacting with the Linear GraphQL API."""
    
    def __init__(self, config, logger):
        """Initialize the Linear API client."""
        self.config = config
        self.logger = logger
        self.api_url = config.get("linear.api_url", "https://api.linear.app/graphql")
        
        # Initialize authenticator
        auth_method = config.get("linear.auth.method", "api_key")
        if auth_method == "api_key":
            self.authenticator = ApiKeyAuthenticator(config)
        elif auth_method == "oauth":
            self.authenticator = OAuthAuthenticator(config)
        else:
            raise ValueError(f"Unsupported authentication method: {auth_method}")
        
        # Configure rate limiting
        self.max_retries = config.get("linear.rate_limit.max_retries", 3)
        self.retry_delay = config.get("linear.rate_limit.retry_delay", 1000)
        self.exponential_backoff = config.get("linear.rate_limit.exponential_backoff", True)
        
        # Create session
        self.session = None
    
    async def initialize(self):
        """Initialize the client session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the client session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against the Linear API."""
        await self.initialize()
        
        # Get authentication headers
        if user_id and hasattr(self.authenticator, "get_auth_headers_for_user"):
            headers = self.authenticator.get_auth_headers_for_user(user_id)
        else:
            headers = self.authenticator.get_auth_headers()
        
        # Add content type header
        headers["Content-Type"] = "application/json"
        
        # Prepare request payload
        payload = {
            "query": query
        }
        
        if variables:
            payload["variables"] = variables
        
        # Log request
        self.logger.debug(
            "Linear API request",
            extra={
                "request_id": request_id,
                "query": query,
                "variables": self._sanitize_variables(variables)
            }
        )
        
        # Execute request with retry logic
        retries = 0
        while True:
            try:
                start_time = time.time()
                async with self.session.post(self.api_url, json=payload, headers=headers) as response:
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # Handle HTTP errors
                    if response.status != 200:
                        await self._handle_http_error(response, duration_ms, request_id)
                    
                    # Parse response
                    response_data = await response.json()
                    
                    # Log response
                    self.logger.debug(
                        "Linear API response",
                        extra={
                            "request_id": request_id,
                            "duration_ms": duration_ms,
                            "status": response.status,
                            "has_data": "data" in response_data,
                            "has_errors": "errors" in response_data
                        }
                    )
                    
                    # Handle GraphQL errors
                    if "errors" in response_data:
                        self._handle_graphql_errors(response_data["errors"], duration_ms, request_id)
                    
                    return response_data
            
            except RateLimitError as e:
                retries += 1
                if retries > self.max_retries:
                    self.logger.error(
                        f"Rate limit exceeded after {retries} retries",
                        extra={"request_id": request_id}
                    )
                    raise
                
                # Calculate retry delay
                retry_after = e.details.get("retry_after")
                if retry_after:
                    delay = int(retry_after) * 1000  # Convert to milliseconds
                else:
                    delay = self.retry_delay * (2 ** (retries - 1) if self.exponential_backoff else 1)
                
                self.logger.warning(
                    f"Rate limit exceeded, retrying in {delay}ms (attempt {retries}/{self.max_retries})",
                    extra={"request_id": request_id}
                )
                
                await asyncio.sleep(delay / 1000)  # Convert to seconds
            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                retries += 1
                if retries > self.max_retries:
                    self.logger.error(
                        f"Request failed after {retries} retries: {str(e)}",
                        extra={"request_id": request_id}
                    )
                    raise LinearApiError(
                        code="NETWORK_ERROR",
                        message="Network error while communicating with Linear API",
                        details={"original_error": str(e)}
                    )
                
                # Calculate retry delay
                delay = self.retry_delay * (2 ** (retries - 1) if self.exponential_backoff else 1)
                
                self.logger.warning(
                    f"Request failed, retrying in {delay}ms (attempt {retries}/{self.max_retries}): {str(e)}",
                    extra={"request_id": request_id}
                )
                
                await asyncio.sleep(delay / 1000)  # Convert to seconds
    
    async def _handle_http_error(self, response, duration_ms, request_id):
        """Handle HTTP errors from the Linear API."""
        try:
            error_text = await response.text()
            error_data = json.loads(error_text)
        except (json.JSONDecodeError, aiohttp.ClientError):
            error_data = {"message": error_text}
        
        self.logger.error(
            f"Linear API HTTP error: {response.status}",
            extra={
                "request_id": request_id,
                "status": response.status,
                "duration_ms": duration_ms,
                "error": error_data
            }
        )
        
        if response.status == 401:
            raise LinearApiError(
                code="AUTHENTICATION_ERROR",
                message="Authentication failed with Linear API",
                details={"status": response.status, "response": error_data}
            )
        elif response.status == 403:
            raise LinearApiError(
                code="PERMISSION_DENIED",
                message="Permission denied by Linear API",
                details={"status": response.status, "response": error_data}
            )
        elif response.status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                message="Linear API rate limit exceeded",
                details={
                    "status": response.status,
                    "response": error_data,
                    "retry_after": retry_after
                }
            )
        elif response.status >= 500:
            raise LinearApiError(
                code="SERVER_ERROR",
                message="Linear API server error",
                details={"status": response.status, "response": error_data}
            )
        else:
            raise LinearApiError(
                code="HTTP_ERROR",
                message=f"HTTP error {response.status} from Linear API",
                details={"status": response.status, "response": error_data}
            )
    
    def _handle_graphql_errors(self, errors, duration_ms, request_id):
        """Handle GraphQL errors from the Linear API."""
        self.logger.error(
            "Linear API GraphQL errors",
            extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "errors": errors
            }
        )
        
        first_error = errors[0]
        error_code = first_error.get("extensions", {}).get("code", "UNKNOWN")
        
        if error_code == "AUTHENTICATION_ERROR":
            raise LinearApiError(
                code="AUTHENTICATION_ERROR",
                message="Authentication failed with Linear API",
                details={"graphql_errors": errors}
            )
        elif error_code == "RATE_LIMITED":
            raise RateLimitError(
                message="Linear API rate limit exceeded",
                details={
                    "graphql_errors": errors,
                    "retry_after": first_error.get("extensions", {}).get("retryAfter")
                }
            )
        elif error_code == "PERMISSION_ERROR":
            raise LinearApiError(
                code="PERMISSION_DENIED",
                message="Permission denied by Linear API",
                details={"graphql_errors": errors}
            )
        else:
            raise LinearApiError(
                code=error_code,
                message=first_error.get("message", "Unknown GraphQL error"),
                details={"graphql_errors": errors}
            )
    
    def _sanitize_variables(self, variables):
        """Sanitize variables to remove sensitive data for logging."""
        if not variables:
            return variables
        
        # Create a copy to avoid modifying the original
        sanitized = json.loads(json.dumps(variables))
        
        # Sanitize sensitive fields
        sensitive_fields = ["token", "apiKey", "password", "secret"]
        
        def sanitize_dict(d):
            for key, value in list(d.items()):
                if key in sensitive_fields:
                    d[key] = "***REDACTED***"
                elif isinstance(value, dict):
                    sanitize_dict(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            sanitize_dict(item)
        
        if isinstance(sanitized, dict):
            sanitize_dict(sanitized)
        
        return sanitized
```

### 4. Feature List Processor

```python
# src/linear/feature_list.py
import json
import re
import markdown
from typing import Any, Dict, List, Optional, Tuple, Union

from ..utils.errors import ValidationError

class FeatureListProcessor:
    """Processor for converting feature lists to Linear issues."""
    
    def __init__(self, config, linear_client, logger):
        """Initialize the feature list processor."""
        self.config = config
        self.linear_client = linear_client
        self.logger = logger
        
        # Configure feature list processing
        self.max_batch_size = config.get("linear.feature_list.max_batch_size", 50)
        self.markdown_support = config.get("linear.feature_list.parsing.markdown_support", True)
        self.json_support = config.get("linear.feature_list.parsing.json_support", True)
        self.extract_metadata = config.get("linear.feature_list.parsing.extract_metadata", True)
        
        # Default values
        self.default_team_id = config.get("linear.feature_list.default_team_id", "")
        self.default_project_id = config.get("linear.feature_list.default_project_id", "")
        self.default_label_ids = config.get("linear.feature_list.default_label_ids", [])
        self.default_state_id = config.get("linear.feature_list.default_state_id", "")
        self.default_assignee_id = config.get("linear.feature_list.default_assignee_id", "")
    
    async def process_feature_list(self, feature_list: str, options: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a feature list and create Linear issues."""
        # Detect format and parse features
        format_type = options.get("format", "auto")
        if format_type == "auto":
            format_type = self._detect_format(feature_list)
        
        self.logger.info(
            f"Processing feature list in {format_type} format",
            extra={"request_id": request_id, "format": format_type}
        )
        
        # Parse features based on format
        if format_type == "json":
            features, global_metadata = self._parse_json_features(feature_list)
        elif format_type == "markdown":
            features, global_metadata = self._parse_markdown_features(feature_list)
        else:  # text
            features, global_metadata = self._parse_text_features(feature_list)
        
        # Validate features
        if not features:
            raise ValidationError(
                message="No valid features found in the feature list",
                details={"format": format_type}
            )
        
        if len(features) > self.max_batch_size:
            raise ValidationError(
                message=f"Too many features in the list (maximum {self.max_batch_size})",
                details={"feature_count": len(features), "max_batch_size": self.max_batch_size}
            )
        
        # Merge options with global metadata
        merged_options = {**global_metadata, **options}
        
        # Create issues
        created_issues = []
        failed_features = []
        
        for feature in features:
            try:
                # Merge feature metadata with options
                issue_data = self._prepare_issue_data(feature, merged_options)
                
                # Create issue
                issue = await self._create_issue(issue_data, request_id)
                
                created_issues.append({
                    "id": issue["id"],
                    "title": issue["title"],
                    "url": f"https://linear.app/issue/{issue['identifier']}"
                })
                
                self.logger.info(
                    f"Created issue: {issue['title']} ({issue['identifier']})",
                    extra={"request_id": request_id, "issue_id": issue["id"]}
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to create issue for feature: {feature.get('title')}",
                    extra={"request_id": request_id, "error": str(e)},
                    exc_info=True
                )
                
                failed_features.append({
                    "title": feature.get("title", "Unknown feature"),
                    "error": str(e)
                })
        
        # Return results
        return {
            "success": len(failed_features) == 0,
            "createdIssues": created_issues,
            "failedFeatures": failed_features
        }
    
    def _detect_format(self, feature_list: str) -> str:
        """Detect the format of the feature list."""
        # Check for JSON format
        if self.json_support and feature_list.strip().startswith("{"):
            try:
                json.loads(feature_list)
                return "json"
            except json.JSONDecodeError:
                pass
        
        # Check for Markdown format
        if self.markdown_support and ("##" in feature_list or "- " in feature_list):
            return "markdown"
        
        # Default to plain text
        return "text"
    
    def _parse_json_features(self, feature_list: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Parse features from JSON format."""
        try:
            data = json.loads(feature_list)
            
            if not isinstance(data, dict):
                raise ValidationError(
                    message="Invalid JSON format: root must be an object",
                    details={"received_type": type(data).__name__}
                )
            
            features = data.get("features", [])
            if not isinstance(features, list):
                raise ValidationError(
                    message="Invalid JSON format: 'features' must be an array",
                    details={"received_type": type(features).__name__}
                )
            
            global_metadata = data.get("metadata", {})
            if not isinstance(global_metadata, dict):
                raise ValidationError(
                    message="Invalid JSON format: 'metadata' must be an object",
                    details={"received_type": type(global_metadata).__name__}
                )
            
            # Validate each feature
            for i, feature in enumerate(features):
                if not isinstance(feature, dict):
                    raise ValidationError(
                        message=f"Invalid feature at index {i}: must be an object",
                        details={"received_type": type(feature).__name__}
                    )
                
                if "title" not in feature:
                    raise ValidationError(
                        message=f"Invalid feature at index {i}: missing required field 'title'",
                        details={"feature": feature}
                    )
            
            return features, global_metadata
        
        except json.JSONDecodeError as e:
            raise ValidationError(
                message="Invalid JSON format",
                details={"error": str(e)}
            )
    
    def _parse_markdown_features(self, feature_list: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Parse features from Markdown format."""
        features = []
        global_metadata = {}
        
        # Split into lines
        lines = feature_list.split("\n")
        
        current_feature = None
        current_section = None
        
        for line in lines:
            # Check for headings
            if line.startswith("# "):
                # Level 1 heading - treat as section title, not a feature
                current_section = line[2:].strip()
                current_feature = None
            elif line.startswith("## "):
                # Level 2 heading - treat as feature title
                if current_feature:
                    features.append(current_feature)
                
                current_feature = {
                    "title": line[3:].strip(),
                    "description": ""
                }
            elif line.startswith("- ") and self.extract_metadata:
                # List item - check for metadata
                if current_feature:
                    item = line[2:].strip()
                    metadata_match = re.match(r"^([^:]+):\s*(.+)$", item)
                    
                    if metadata_match:
                        key = metadata_match.group(1).lower()
                        value = metadata_match.group(2).strip()
                        
                        # Map common metadata keys
                        if key == "priority":
                            current_feature["priority"] = self._parse_priority(value)
                        elif key == "description":
                            current_feature["description"] = value
                        elif key == "labels" or key == "tags":
                            current_feature["labels"] = [label.strip() for label in value.split(",")]
                        elif key == "assignee":
                            current_feature["assignee"] = value
                        elif key == "estimate":
                            try:
                                current_feature["estimate"] = float(value)
                            except ValueError:
                                pass
                        else:
                            # Store as custom metadata
                            if "metadata" not in current_feature:
                                current_feature["metadata"] = {}
                            current_feature["metadata"][key] = value
                    else:
                        # Regular list item - add to description
                        if current_feature["description"]:
                            current_feature["description"] += "\n"
                        current_feature["description"] += f"- {item}"
            else:
                # Regular line - add to description if part of a feature
                if current_feature and line.strip():
                    if current_feature["description"]:
                        current_feature["description"] += "\n"
                    current_feature["description"] += line
        
        # Add the last feature if there is one
        if current_feature:
            features.append(current_feature)
        
        return features, global_metadata
    
    def _parse_text_features(self, feature_list: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Parse features from plain text format."""
        features = []
        global_metadata = {}
        
        # Split into lines
        lines = feature_list.split("\n")
        
        for line in lines:
            line = line.strip()
            if line:
                features.append({
                    "title": line,
                    "description": ""
                })
        
        return features, global_metadata
    
    def _prepare_issue_data(self, feature: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare issue data for creation."""
        issue_data = {
            "title": feature["title"],
            "description": feature.get("description", "")
        }
        
        # Add team ID
        team_id = options.get("teamId") or feature.get("teamId") or self.default_team_id
        if team_id:
            issue_data["teamId"] = team_id
        
        # Add project ID
        project_id = options.get("projectId") or feature.get("projectId") or self.default_project_id
        if project_id:
            issue_data["projectId"] = project_id
        
        # Add state ID
        state_id = options.get("stateId") or feature.get("stateId") or self.default_state_id
        if state_id:
            issue_data["stateId"] = state_id
        
        # Add assignee ID
        assignee_id = options.get("assigneeId") or feature.get("assigneeId") or self.default_assignee_id
        if assignee_id:
            issue_data["assigneeId"] = assignee_id
        
        # Add priority
        priority = options.get("priority") or feature.get("priority")
        if priority is not None:
            issue_data["priority"] = priority
        
        # Add labels
        label_ids = options.get("labelIds", []) or self.default_label_ids
        if label_ids:
            issue_data["labelIds"] = label_ids
        
        # Add parent issue ID
        parent_issue_id = options.get("parentIssueId") or feature.get("parentIssueId")
        if parent_issue_id:
            issue_data["parentId"] = parent_issue_id
        
        # Add estimate
        estimate = options.get("estimate") or feature.get("estimate")
        if estimate is not None:
            issue_data["estimate"] = estimate
        
        return issue_data
    
    async def _create_issue(self, issue_data: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
        """Create an issue in Linear."""
        query = """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              title
              identifier
            }
          }
        }
        """
        
        variables = {
            "input": issue_data
        }
        
        response = await self.linear_client.execute_query(query, variables, request_id=request_id)
        
        if not response.get("data", {}).get("issueCreate", {}).get("success"):
            raise ValidationError(
                message="Failed to create issue",
                details={"response": response}
            )
        
        return response["data"]["issueCreate"]["issue"]
    
    def _parse_priority(self, priority_str: str) -> int:
        """Parse priority string to Linear priority value."""
        priority_map = {
            "urgent": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
            "no priority": 0
        }
        
        priority_str = priority_str.lower()
        
        if priority_str in priority_map:
            return priority_map[priority_str]
        
        try:
            priority_int = int(priority_str)
            if 0 <= priority_int <= 4:
                return priority_int
        except ValueError:
            pass
        
        return 0  # Default to no priority
```

### 5. MCP Server Implementation

```python
# src/server.py
import asyncio
import json
import logging
import uuid
import websockets
from typing import Any, Dict, List, Optional, Set, Union

from .config import Config
from .mcp.connection import McpConnection
from .mcp.message import McpMessage, McpProtocolError
from .linear.client import LinearClient
from .linear.feature_list import FeatureListProcessor
from .linear.search import SearchEngine
from .utils.errors import ErrorHandler
from .utils.logging import configure_logging

class McpServer:
    """MCP server for Linear integration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the MCP server."""
        # Load configuration
        self.config = Config(config_path)
        
        # Configure logging
        self.logger = configure_logging(self.config)
        
        # Initialize error handler
        self.error_handler = ErrorHandler(self.logger)
        
        # Initialize Linear client
        self.linear_client = LinearClient(self.config, self.logger)
        
        # Initialize feature list processor
        self.feature_list_processor = FeatureListProcessor(self.config, self.linear_client, self.logger)
        
        # Initialize search engine
        self.search_engine = SearchEngine(self.config, self.linear_client, self.logger)
        
        # Active connections
        self.connections: Set[McpConnection] = set()
        
        # Server state
        self.running = False
        self.server = None
    
    async def start(self):
        """Start the MCP server."""
        if self.running:
            return
        
        # Initialize Linear client
        await self.linear_client.initialize()
        
        # Get server configuration
        host = self.config.get("server.host", "0.0.0.0")
        port = self.config.get("server.port", 8080)
        
        # Start WebSocket server
        self.server = await websockets.serve(
            self.handle_connection,
            host,
            port,
            ping_interval=30,
            ping_timeout=10,
            max_size=10 * 1024 * 1024  # 10 MB max message size
        )
        
        self.running = True
        self.logger.info(f"MCP server started on {host}:{port}")
    
    async def stop(self):
        """Stop the MCP server."""
        if not self.running:
            return
        
        # Close all connections
        close_tasks = [conn.close() for conn in self.connections]
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Close Linear client
        await self.linear_client.close()
        
        self.running = False
        self.logger.info("MCP server stopped")
    
    async def handle_connection(self, websocket, path):
        """Handle a new WebSocket connection."""
        connection_id = str(uuid.uuid4())
        connection = McpConnection(connection_id, websocket, self.logger)
        
        self.connections.add(connection)
        self.logger.info(f"New connection established: {connection_id}")
        
        try:
            # Handle connection initialization
            await self.handle_initialization(connection)
            
            # Handle messages
            async for message in websocket:
                await self.handle_message(connection, message)
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.info(f"Connection closed: {connection_id} (code: {e.code}, reason: {e.reason})")
        except Exception as e:
            self.logger.error(f"Error handling connection: {str(e)}", exc_info=True)
        finally:
            # Remove connection
            self.connections.remove(connection)
            self.logger.info(f"Connection removed: {connection_id}")
    
    async def handle_initialization(self, connection: McpConnection):
        """Handle connection initialization."""
        # Wait for initialize request
        message = await connection.receive()
        
        try:
            # Parse and validate message
            request = McpMessage.parse(message)
            McpMessage.validate_request(request)
            
            # Check for initialize method
            if request["method"] != "initialize":
                raise McpProtocolError(
                    message="First message must be initialize request",
                    details={"received_method": request["method"]}
                )
            
            # Process initialize request
            params = request.get("params", {})
            client_capabilities = params.get("capabilities", {})
            
            # Prepare server capabilities
            server_capabilities = {
                "resources": self.config.get("mcp.capabilities.resources", True),
                "tools": self.config.get("mcp.capabilities.tools", True),
                "prompts": self.config.get("mcp.capabilities.prompts", False),
                "sampling": self.config.get("mcp.capabilities.sampling", False)
            }
            
            # Create response
            response = McpMessage.create_response(request["id"], {
                "capabilities": server_capabilities,
                "serverInfo": {
                    "name": "Linear MCP Server",
                    "version": "1.0.0"
                }
            })
            
            # Send response
            await connection.send(json.dumps(response))
            
            # Store client capabilities
            connection.client_capabilities = client_capabilities
            
            self.logger.info(f"Connection initialized: {connection.id}")
        except Exception as e:
            # Handle initialization error
            error_response = self.error_handler.handle_exception(e)
            await connection.send(json.dumps(error_response))
            raise
    
    async def handle_message(self, connection: McpConnection, message: str):
        """Handle an incoming message."""
        request_id = str(uuid.uuid4())
        
        try:
            # Parse and validate message
            request = McpMessage.parse(message)
            McpMessage.validate_request(request)
            
            # Log request
            self.logger.info(
                f"Received request: {request['method']}",
                extra={
                    "request_id": request_id,
                    "connection_id": connection.id,
                    "method": request["method"],
                    "id": request["id"]
                }
            )
            
            # Process request
            if request["method"] == "getResource":
                response = await self.handle_get_resource(request, request_id)
            elif request["method"] == "executeTool":
                response = await self.handle_execute_tool(request, request_id)
            else:
                raise McpProtocolError(
                    message=f"Unsupported method: {request['method']}",
                    details={"supported_methods": ["getResource", "executeTool"]}
                )
            
            # Send response
            await connection.send(json.dumps(response))
            
            # Log response
            self.logger.info(
                f"Sent response for request: {request['id']}",
                extra={
                    "request_id": request_id,
                    "connection_id": connection.id,
                    "method": request["method"],
                    "id": request["id"]
                }
            )
        except Exception as e:
            # Handle error
            error_response = self.error_handler.handle_exception(e, request_id)
            error_response["id"] = request.get("id") if isinstance(request, dict) else None
            
            # Send error response
            await connection.send(json.dumps(error_response))
            
            # Log error
            self.logger.error(
                f"Error handling request: {str(e)}",
                extra={
                    "request_id": request_id,
                    "connection_id": connection.id
                },
                exc_info=True
            )
    
    async def handle_get_resource(self, request: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle a getResource request."""
        params = request.get("params", {})
        resource_name = params.get("name")
        resource_params = params.get("parameters", {})
        
        if not resource_name:
            raise McpProtocolError(
                message="Missing required parameter: name",
                details={"received_params": params}
            )
        
        # Handle different resources
        if resource_name == "issues":
            result = await self.search_engine.search_issues(resource_params, request_id)
        elif resource_name == "projects":
            result = await self.search_engine.search_projects(resource_params, request_id)
        elif resource_name == "search":
            result = await self.search_engine.unified_search(resource_params, request_id)
        else:
            raise McpProtocolError(
                message=f"Unsupported resource: {resource_name}",
                details={"supported_resources": ["issues", "projects", "search"]}
            )
        
        return McpMessage.create_response(request["id"], result)
    
    async def handle_execute_tool(self, request: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle an executeTool request."""
        params = request.get("params", {})
        tool_name = params.get("name")
        tool_params = params.get("parameters", {})
        
        if not tool_name:
            raise McpProtocolError(
                message="Missing required parameter: name",
                details={"received_params": params}
            )
        
        # Handle different tools
        if tool_name == "createWorkItemsFromFeatureList":
            result = await self.feature_list_processor.process_feature_list(
                tool_params.get("featureList", ""),
                {k: v for k, v in tool_params.items() if k != "featureList"},
                request_id
            )
        else:
            raise McpProtocolError(
                message=f"Unsupported tool: {tool_name}",
                details={"supported_tools": ["createWorkItemsFromFeatureList"]}
            )
        
        return McpMessage.create_response(request["id"], result)


async def main():
    """Main entry point for the MCP server."""
    import argparse
    import signal
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Linear MCP Server")
    parser.add_argument("--config", help="Path to configuration file")
    args = parser.parse_args()
    
    # Create server
    server = McpServer(args.config)
    
    # Handle signals
    loop = asyncio.get_event_loop()
    
    async def shutdown(signal, loop):
        """Shutdown the server gracefully."""
        server.logger.info(f"Received signal {signal.name}, shutting down...")
        await server.stop()
        loop.stop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))
    
    # Start server
    try:
        await server.start()
        
        # Keep running
        while server.running:
            await asyncio.sleep(1)
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

## Implementation Sequence

The implementation should follow this sequence to ensure dependencies are properly handled:

1. **Setup Project Structure**
   - Create directory structure
   - Initialize Git repository
   - Create basic README.md

2. **Configuration Management**
   - Implement configuration loading
   - Define default configuration
   - Add environment variable support

3. **Logging and Error Handling**
   - Implement logging utilities
   - Define error classes
   - Create error handling middleware

4. **Linear API Integration**
   - Implement API client
   - Add authentication support
   - Create data models

5. **MCP Protocol Implementation**
   - Implement message handling
   - Add connection management
   - Define resource and tool interfaces

6. **Feature List Processing**
   - Implement feature list parsing
   - Add issue creation logic
   - Handle metadata extraction

7. **Search Functionality**
   - Implement search engine
   - Add query translation
   - Create result formatting

8. **Server Implementation**
   - Create main server class
   - Add request handling
   - Implement WebSocket support

9. **Testing**
   - Write unit tests
   - Add integration tests
   - Create test fixtures

10. **Documentation**
    - Write API documentation
    - Create usage guide
    - Add configuration reference

11. **Deployment**
    - Create Dockerfile
    - Add Docker Compose configuration
    - Write deployment scripts

## Technical Considerations

### Dependencies

The implementation will require the following key dependencies:

- **Python 3.8+**: For modern language features
- **websockets**: For WebSocket server implementation
- **aiohttp**: For HTTP client to interact with Linear API
- **pyyaml**: For configuration file parsing
- **markdown**: For Markdown parsing in feature lists
- **pytest**: For testing
- **pytest-asyncio**: For testing async code

### Performance Optimization

To ensure good performance, the implementation should:

1. **Use Asynchronous I/O**
   - Implement all I/O operations asynchronously
   - Use asyncio for concurrency
   - Handle multiple connections efficiently

2. **Implement Caching**
   - Cache frequently accessed Linear metadata
   - Cache search results with appropriate TTL
   - Implement efficient cache invalidation

3. **Optimize API Usage**
   - Batch API requests when possible
   - Request only necessary fields
   - Implement rate limit handling

4. **Memory Management**
   - Limit message sizes
   - Clean up resources properly
   - Avoid memory leaks in long-running processes

### Security Considerations

The implementation must address these security concerns:

1. **Authentication**
   - Secure storage of API keys
   - Proper validation of client credentials
   - Support for OAuth if needed

2. **Data Protection**
   - TLS/SSL for all communications
   - Sanitization of sensitive data in logs
   - Proper error handling to avoid information leakage

3. **Input Validation**
   - Validate all client inputs
   - Implement proper schema validation
   - Protect against injection attacks

4. **Rate Limiting**
   - Implement rate limiting for client requests
   - Handle Linear API rate limits gracefully
   - Prevent abuse of server resources

## Conclusion

This implementation blueprint provides a comprehensive guide for developing the Linear MCP server. By following this blueprint, developers can create a robust, efficient, and secure server that integrates Linear's API with the Model Context Protocol, enabling powerful workflows for creating work items from feature lists and implementing comprehensive search functionality.

The modular design allows for easy extension and maintenance, while the detailed implementation examples provide clear guidance for each component. The implementation sequence ensures that dependencies are properly handled, and the technical considerations address important aspects of performance, security, and reliability.

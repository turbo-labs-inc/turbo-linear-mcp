# MCP Server Configuration for Linear Integration

## Overview
This document defines the configuration structure for the MCP server that integrates with Linear's API. The configuration is designed to be flexible, secure, and easy to maintain.

## Configuration Format
The configuration will be stored in a YAML file format for readability and maintainability. JSON is also supported as an alternative.

## Configuration Structure

```yaml
# MCP Server Configuration for Linear Integration

# Server settings
server:
  # Host and port for the MCP server
  host: "0.0.0.0"
  port: 8080
  
  # Maximum number of concurrent connections
  max_connections: 100
  
  # Timeout settings (in seconds)
  connection_timeout: 30
  request_timeout: 60
  
  # Enable debug mode (provides more verbose logging)
  debug: false

# MCP protocol settings
mcp:
  # Protocol version
  version: "2025-03-26"
  
  # Supported capabilities
  capabilities:
    resources: true
    tools: true
    prompts: false
    sampling: false
  
  # Resource configuration
  resources:
    # Maximum resources per response
    max_per_page: 50
    
    # Cache settings
    cache_enabled: true
    cache_ttl: 300  # seconds
  
  # Tool configuration
  tools:
    # Maximum execution time (in seconds)
    max_execution_time: 120
    
    # Rate limiting for tool executions
    rate_limit:
      enabled: true
      max_per_minute: 60

# Linear API integration
linear:
  # API endpoint
  api_url: "https://api.linear.app/graphql"
  
  # Authentication
  auth:
    # Authentication method: "api_key" or "oauth"
    method: "api_key"
    
    # API key (can be overridden by environment variable LINEAR_API_KEY)
    api_key: ""
    
    # OAuth settings (if using OAuth)
    oauth:
      client_id: ""
      client_secret: ""
      redirect_uri: ""
  
  # Rate limiting handling
  rate_limit:
    # Maximum retries for rate-limited requests
    max_retries: 3
    
    # Base delay between retries (in milliseconds)
    retry_delay: 1000
    
    # Use exponential backoff for retries
    exponential_backoff: true
  
  # Feature list processing
  feature_list:
    # Default team ID for new issues (if not specified)
    default_team_id: ""
    
    # Default project ID for new issues (if not specified)
    default_project_id: ""
    
    # Default label IDs for new issues
    default_label_ids: []
    
    # Default state ID for new issues
    default_state_id: ""
    
    # Default assignee ID for new issues
    default_assignee_id: ""
    
    # Maximum features to process in a single batch
    max_batch_size: 50
    
    # Feature parsing settings
    parsing:
      # Support markdown format
      markdown_support: true
      
      # Support JSON format
      json_support: true
      
      # Extract metadata from feature descriptions
      extract_metadata: true
  
  # Search settings
  search:
    # Maximum search results per page
    max_results_per_page: 25
    
    # Default fields to return in search results
    default_fields: ["id", "title", "description", "state", "assignee", "labels", "project"]
    
    # Cache search results
    cache_results: true
    
    # Cache TTL (in seconds)
    cache_ttl: 60

# Logging configuration
logging:
  # Log level: "debug", "info", "warning", "error", "critical"
  level: "info"
  
  # Log format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # Log file path (if empty, logs to stdout)
  file: ""
  
  # Maximum log file size before rotation (in MB)
  max_size: 10
  
  # Number of backup log files to keep
  backup_count: 5
  
  # Log HTTP requests
  log_requests: true
  
  # Log Linear API calls
  log_api_calls: true

# Security settings
security:
  # Enable TLS/SSL
  ssl:
    enabled: false
    cert_file: ""
    key_file: ""
  
  # CORS settings
  cors:
    enabled: true
    allowed_origins: ["*"]
    allowed_methods: ["GET", "POST"]
    allowed_headers: ["Content-Type", "Authorization"]
  
  # API key for accessing the MCP server (if empty, no authentication required)
  api_key: ""
```

## Environment Variable Overrides
For security and deployment flexibility, sensitive configuration values can be overridden using environment variables:

| Environment Variable | Configuration Path | Description |
|----------------------|-------------------|-------------|
| `LINEAR_MCP_SERVER_HOST` | `server.host` | Server host |
| `LINEAR_MCP_SERVER_PORT` | `server.port` | Server port |
| `LINEAR_API_KEY` | `linear.auth.api_key` | Linear API key |
| `LINEAR_OAUTH_CLIENT_ID` | `linear.auth.oauth.client_id` | OAuth client ID |
| `LINEAR_OAUTH_CLIENT_SECRET` | `linear.auth.oauth.client_secret` | OAuth client secret |
| `LINEAR_MCP_API_KEY` | `security.api_key` | MCP server API key |
| `LINEAR_MCP_LOG_LEVEL` | `logging.level` | Log level |
| `LINEAR_MCP_LOG_FILE` | `logging.file` | Log file path |

## Configuration Loading Process
1. Load default configuration values
2. Override with values from configuration file
3. Override with environment variables
4. Validate configuration (check for required values, validate formats, etc.)
5. Apply configuration to server components

## Configuration Validation
The server will validate the configuration during startup and report any issues:
- Required fields are present
- Values are of the correct type
- Values are within acceptable ranges
- Interdependent configuration is consistent

## Sensitive Data Handling
- API keys and secrets are never logged
- When logging configuration, sensitive fields are masked
- Sensitive data is only stored in memory when needed

## Example Minimal Configuration
A minimal configuration file might look like:

```yaml
server:
  port: 8080

linear:
  auth:
    method: "api_key"
    # API key provided via LINEAR_API_KEY environment variable

logging:
  level: "info"
```

## Configuration Updates
The server can reload its configuration without restart by sending a SIGHUP signal or calling a dedicated admin endpoint.

This configuration structure provides flexibility for different deployment scenarios while maintaining security and ease of use.

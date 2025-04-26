# Error Handling and Logging Approach for Linear MCP Server

## Overview
This document outlines the error handling and logging approach for the Linear MCP server. A robust error handling and logging system is essential for maintaining server reliability, facilitating debugging, and providing a good user experience.

## Error Handling Strategy

### Error Classification

Errors in the Linear MCP server will be classified into the following categories:

1. **Client Errors (4xx)**
   - Invalid requests from MCP clients
   - Authentication failures
   - Permission issues
   - Resource not found
   - Rate limiting

2. **Server Errors (5xx)**
   - Internal server errors
   - Linear API errors
   - Dependency failures
   - Configuration errors
   - Unexpected exceptions

3. **Linear API Errors**
   - Authentication failures
   - Rate limiting
   - Resource not found
   - Permission issues
   - Validation errors
   - Service unavailable

4. **MCP Protocol Errors**
   - Invalid message format
   - Unsupported capabilities
   - Protocol version mismatch
   - Message size limits

### Error Handling Principles

The error handling system will follow these principles:

1. **Fail Gracefully**
   - Prevent cascading failures
   - Provide meaningful fallbacks when possible
   - Maintain system stability

2. **Provide Clear Information**
   - Return descriptive error messages to clients
   - Include error codes for programmatic handling
   - Offer suggestions for resolution when applicable

3. **Maintain Security**
   - Avoid exposing sensitive information in error messages
   - Provide detailed internal logs while keeping client messages generic
   - Prevent information leakage through error responses

4. **Enable Debugging**
   - Log sufficient context for troubleshooting
   - Include correlation IDs for request tracing
   - Capture stack traces for unexpected errors

### Error Response Format

Error responses to MCP clients will follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Specific field with error (if applicable)",
      "reason": "Detailed reason for the error",
      "suggestion": "Suggested action to resolve the error (if applicable)"
    },
    "requestId": "unique-request-identifier-for-tracing"
  }
}
```

### Error Handling Implementation

#### 1. Global Error Handler

```python
class ErrorHandler:
    def __init__(self, logger):
        self.logger = logger
    
    async def handle_exception(self, request, exception):
        # Generate unique request ID if not already present
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Determine error type and code
        error_code, status_code, message = self._classify_exception(exception)
        
        # Log the error with appropriate level
        self._log_exception(request, exception, error_code, request_id)
        
        # Create error response
        error_response = {
            "error": {
                "code": error_code,
                "message": message,
                "requestId": request_id
            }
        }
        
        # Add details if available
        if hasattr(exception, "details"):
            error_response["error"]["details"] = exception.details
        
        return JSONResponse(
            status_code=status_code,
            content=error_response
        )
    
    def _classify_exception(self, exception):
        # Map exception types to error codes and status codes
        if isinstance(exception, AuthenticationError):
            return "AUTHENTICATION_ERROR", 401, "Authentication failed"
        elif isinstance(exception, PermissionError):
            return "PERMISSION_DENIED", 403, "Permission denied"
        elif isinstance(exception, ResourceNotFoundError):
            return "RESOURCE_NOT_FOUND", 404, "Resource not found"
        elif isinstance(exception, ValidationError):
            return "VALIDATION_ERROR", 400, "Invalid request"
        elif isinstance(exception, RateLimitError):
            return "RATE_LIMIT_EXCEEDED", 429, "Rate limit exceeded"
        elif isinstance(exception, LinearApiError):
            return f"LINEAR_API_ERROR_{exception.code}", 502, "Error from Linear API"
        elif isinstance(exception, McpProtocolError):
            return "MCP_PROTOCOL_ERROR", 400, "Invalid MCP protocol message"
        else:
            return "INTERNAL_SERVER_ERROR", 500, "Internal server error"
    
    def _log_exception(self, request, exception, error_code, request_id):
        # Determine log level based on error type
        if error_code.startswith("INTERNAL_SERVER_ERROR"):
            log_level = logging.ERROR
        elif error_code.startswith("LINEAR_API_ERROR"):
            log_level = logging.ERROR
        else:
            log_level = logging.WARNING
        
        # Create log context
        context = {
            "request_id": request_id,
            "error_code": error_code,
            "client_ip": request.client.host,
            "method": request.method,
            "path": request.url.path,
            "user_agent": request.headers.get("User-Agent", "Unknown")
        }
        
        # Add exception details
        if hasattr(exception, "details"):
            context["error_details"] = exception.details
        
        # Log the exception with context
        self.logger.log(
            log_level,
            f"Exception during request processing: {str(exception)}",
            extra=context,
            exc_info=True
        )
```

#### 2. Linear API Error Handling

```python
class LinearApiClient:
    # ... other methods ...
    
    async def execute_query(self, query, variables=None):
        try:
            # Execute GraphQL query
            response = await self._send_request(query, variables)
            
            # Check for GraphQL errors
            if "errors" in response:
                self._handle_graphql_errors(response["errors"])
            
            return response["data"]
        except aiohttp.ClientResponseError as e:
            # Handle HTTP errors
            self._handle_http_error(e)
        except aiohttp.ClientError as e:
            # Handle network errors
            raise LinearApiError(
                code="NETWORK_ERROR",
                message="Network error while communicating with Linear API",
                details={"original_error": str(e)}
            )
        except json.JSONDecodeError:
            # Handle invalid JSON response
            raise LinearApiError(
                code="INVALID_RESPONSE",
                message="Invalid response from Linear API",
                details={"response": await response.text()}
            )
    
    def _handle_graphql_errors(self, errors):
        # Process GraphQL errors
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
    
    def _handle_http_error(self, error):
        # Handle HTTP errors from Linear API
        if error.status == 401:
            raise LinearApiError(
                code="AUTHENTICATION_ERROR",
                message="Authentication failed with Linear API",
                details={"status": error.status, "message": error.message}
            )
        elif error.status == 403:
            raise LinearApiError(
                code="PERMISSION_DENIED",
                message="Permission denied by Linear API",
                details={"status": error.status, "message": error.message}
            )
        elif error.status == 429:
            raise RateLimitError(
                message="Linear API rate limit exceeded",
                details={
                    "status": error.status,
                    "message": error.message,
                    "retry_after": error.headers.get("Retry-After")
                }
            )
        elif error.status >= 500:
            raise LinearApiError(
                code="SERVER_ERROR",
                message="Linear API server error",
                details={"status": error.status, "message": error.message}
            )
        else:
            raise LinearApiError(
                code="HTTP_ERROR",
                message=f"HTTP error {error.status} from Linear API",
                details={"status": error.status, "message": error.message}
            )
```

#### 3. MCP Protocol Error Handling

```python
class McpMessageHandler:
    # ... other methods ...
    
    def validate_message(self, message):
        # Validate message format
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
        
        # Validate method or result/error
        if "method" in message:
            # Request message
            if "id" not in message:
                raise McpProtocolError(
                    message="Missing required field for request: id",
                    details={"received_message": message}
                )
            
            if "params" in message and not isinstance(message["params"], (dict, list)):
                raise McpProtocolError(
                    message="Invalid params: must be an object or array",
                    details={"received_params_type": type(message["params"]).__name__}
                )
        elif "result" in message or "error" in message:
            # Response message
            if "id" not in message:
                raise McpProtocolError(
                    message="Missing required field for response: id",
                    details={"received_message": message}
                )
            
            if "error" in message:
                self._validate_error_object(message["error"])
        else:
            raise McpProtocolError(
                message="Message must contain either method or result/error",
                details={"received_message": message}
            )
    
    def _validate_error_object(self, error):
        if not isinstance(error, dict):
            raise McpProtocolError(
                message="Invalid error: must be an object",
                details={"received_error_type": type(error).__name__}
            )
        
        if "code" not in error:
            raise McpProtocolError(
                message="Missing required field in error: code",
                details={"received_error": error}
            )
        
        if not isinstance(error["code"], int):
            raise McpProtocolError(
                message="Invalid error code: must be an integer",
                details={"received_code_type": type(error["code"]).__name__}
            )
        
        if "message" not in error:
            raise McpProtocolError(
                message="Missing required field in error: message",
                details={"received_error": error}
            )
```

## Logging Strategy

### Logging Levels

The logging system will use the following levels:

1. **DEBUG**
   - Detailed information for debugging
   - Request and response payloads
   - Internal state changes
   - Performance metrics

2. **INFO**
   - Normal operation events
   - Server startup and shutdown
   - Configuration loading
   - Client connections and disconnections
   - Successful operations

3. **WARNING**
   - Potential issues that don't affect operation
   - Deprecated feature usage
   - Slow operations
   - Retried operations
   - Client errors

4. **ERROR**
   - Errors that affect specific operations
   - Failed requests to Linear API
   - Unexpected exceptions
   - Configuration errors

5. **CRITICAL**
   - Severe errors that affect server operation
   - Authentication failures
   - Database connection failures
   - Unrecoverable errors

### Log Format

Logs will be structured in a consistent format to facilitate analysis:

```
[TIMESTAMP] [LEVEL] [REQUEST_ID] [COMPONENT] - Message | context_key1=value1 context_key2=value2
```

For JSON logging, the following structure will be used:

```json
{
  "timestamp": "ISO8601 timestamp",
  "level": "INFO|WARNING|ERROR|etc.",
  "request_id": "unique-request-identifier",
  "component": "component-name",
  "message": "Log message",
  "context": {
    "key1": "value1",
    "key2": "value2"
  },
  "exception": {
    "type": "ExceptionType",
    "message": "Exception message",
    "traceback": "Stack trace (if available)"
  }
}
```

### Logging Implementation

#### 1. Logger Configuration

```python
def configure_logging(config):
    # Get logging configuration
    log_level = getattr(logging, config.get("logging.level", "INFO").upper())
    log_format = config.get("logging.format")
    log_file = config.get("logging.file")
    
    # Create logger
    logger = logging.getLogger("linear_mcp_server")
    logger.setLevel(log_level)
    
    # Create formatter
    if config.get("logging.json_format", False):
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(log_format)
    
    # Create handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler (if configured)
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=config.get("logging.max_size", 10) * 1024 * 1024,
            backupCount=config.get("logging.backup_count", 5)
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Add handlers to logger
    for handler in handlers:
        logger.addHandler(handler)
    
    # Configure logging for specific components
    if config.get("logging.log_requests", True):
        logging.getLogger("aiohttp.access").setLevel(log_level)
    
    return logger
```

#### 2. Request Logging Middleware

```python
class RequestLoggingMiddleware:
    def __init__(self, logger):
        self.logger = logger
    
    async def __call__(self, request, handler):
        # Generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Add request ID to request object
        request["request_id"] = request_id
        
        # Log request
        self.logger.info(
            f"Request received: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.remote,
                "user_agent": request.headers.get("User-Agent", "Unknown")
            }
        )
        
        # Process request and measure time
        start_time = time.time()
        try:
            response = await handler(request)
            
            # Log response
            self.logger.info(
                f"Response sent: {response.status}",
                extra={
                    "request_id": request_id,
                    "status": response.status,
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
        except Exception as e:
            # Log exception (will be handled by error handler)
            self.logger.error(
                f"Exception during request processing: {str(e)}",
                extra={
                    "request_id": request_id,
                    "duration_ms": int((time.time() - start_time) * 1000)
                },
                exc_info=True
            )
            raise
```

#### 3. Linear API Call Logging

```python
class LinearApiLogger:
    def __init__(self, logger):
        self.logger = logger
    
    def log_request(self, request_id, query, variables):
        # Sanitize variables to remove sensitive data
        sanitized_variables = self._sanitize_variables(variables)
        
        self.logger.debug(
            "Linear API request",
            extra={
                "request_id": request_id,
                "query": query,
                "variables": sanitized_variables
            }
        )
    
    def log_response(self, request_id, response, duration_ms):
        self.logger.debug(
            "Linear API response",
            extra={
                "request_id": request_id,
                "has_data": "data" in response,
                "has_errors": "errors" in response,
                "duration_ms": duration_ms
            }
        )
        
        if "errors" in response:
            self.logger.warning(
                "Linear API returned errors",
                extra={
                    "request_id": request_id,
                    "errors": response["errors"]
                }
            )
    
    def log_error(self, request_id, error, duration_ms):
        self.logger.error(
            f"Linear API error: {str(error)}",
            extra={
                "request_id": request_id,
                "error_type": type(error).__name__,
                "duration_ms": duration_ms
            },
            exc_info=True
        )
    
    def _sanitize_variables(self, variables):
        if not variables:
            return variables
        
        # Create a copy to avoid modifying the original
        sanitized = copy.deepcopy(variables)
        
        # Sanitize sensitive fields
        sensitive_fields = ["token", "apiKey", "password", "secret"]
        
        def sanitize_dict(d):
            for key, value in d.items():
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

### Log Management

#### 1. Log Rotation
- Implement log rotation to manage file size
- Configure retention period for logs
- Compress older logs

#### 2. Log Aggregation
- Support for sending logs to external systems
- Integration with log aggregation services
- Structured logging for easier analysis

#### 3. Log Analysis
- Include correlation IDs for request tracing
- Log performance metrics for monitoring
- Support for log filtering and searching

## Error Monitoring and Alerting

### 1. Error Tracking
- Track error rates and patterns
- Identify recurring issues
- Monitor error trends over time

### 2. Alerting
- Configure alerts for critical errors
- Set thresholds for error rates
- Notify administrators of significant issues

### 3. Health Checks
- Implement server health endpoints
- Monitor Linear API connectivity
- Check system resource usage

## Conclusion

This error handling and logging approach provides a comprehensive strategy for managing errors and logging in the Linear MCP server. By implementing robust error handling, structured logging, and proper monitoring, the server will be more reliable, easier to debug, and provide a better experience for users.

# Authentication and Security Design for Linear MCP Server

## Overview
This document outlines the authentication and security design for the Linear MCP server. It covers how the server will authenticate with Linear's API, how MCP clients will authenticate with the server, and various security considerations to ensure data protection and secure operations.

## Linear API Authentication

### API Key Authentication
The primary authentication method for the Linear API will be API key authentication:

1. **API Key Management**
   - API keys will be stored securely in the server configuration
   - Environment variables will be used for sensitive credentials
   - Keys will never be logged or exposed in responses

2. **API Key Usage**
   - Keys will be included in the Authorization header for all Linear API requests
   - Format: `Authorization: Bearer <API_KEY>`
   - Keys will be validated on server startup

3. **API Key Rotation**
   - Support for key rotation without server downtime
   - Graceful handling of key expiration or revocation

### OAuth Authentication (Optional)
For multi-user scenarios, OAuth authentication will be supported:

1. **OAuth Flow**
   - Implementation of OAuth 2.0 authorization code flow
   - Secure storage of client ID and client secret
   - Proper handling of redirect URIs

2. **Token Management**
   - Secure storage of access and refresh tokens
   - Automatic token refresh when expired
   - Token revocation on user logout

3. **User Context**
   - Association of requests with authenticated users
   - Respect for user-specific permissions in Linear

## MCP Server Authentication

### Client Authentication
MCP clients will authenticate with the server using one of the following methods:

1. **API Key Authentication**
   - Simple API key validation for MCP clients
   - Keys configured in server configuration
   - Sent via Authorization header

2. **No Authentication**
   - Optional mode for local development or trusted environments
   - All security enforced at the Linear API level

3. **Custom Authentication (Future)**
   - Extensible design to support additional authentication methods
   - Potential integration with SSO or other identity providers

### Authentication Flow

```
┌─────────────┐                ┌─────────────────┐                ┌─────────────┐
│             │                │                 │                │             │
│  MCP Client │───Auth Request─►  MCP Server     │───Auth Request─►  Linear API │
│             │                │                 │                │             │
│             │◄──Auth Response─┤                 │◄──Auth Response┤             │
│             │                │                 │                │             │
└─────────────┘                └─────────────────┘                └─────────────┘
```

1. MCP client sends authentication credentials to MCP server
2. MCP server validates client credentials
3. MCP server uses Linear API credentials for Linear API requests
4. Linear API validates credentials and returns response
5. MCP server processes response and returns to client

## Security Considerations

### Data Protection

1. **Sensitive Data Handling**
   - Credentials and tokens never exposed in logs or responses
   - Sensitive data encrypted at rest
   - Minimal data retention policy

2. **Data Transmission**
   - TLS/SSL for all communications
   - Secure headers (HSTS, CSP, etc.)
   - Protection against MITM attacks

3. **Data Access**
   - Respect Linear permissions model
   - No caching of sensitive data
   - Proper data sanitization

### Attack Prevention

1. **Input Validation**
   - Strict validation of all client inputs
   - Protection against injection attacks
   - Schema validation for all requests

2. **Rate Limiting**
   - Implementation of rate limiting for all endpoints
   - Protection against brute force attacks
   - Graceful handling of rate limit errors

3. **Error Handling**
   - No leakage of sensitive information in error messages
   - Generic error messages for clients
   - Detailed internal logging for debugging

### Secure Configuration

1. **Environment-Based Configuration**
   - Different security settings for development and production
   - Environment variable overrides for sensitive settings
   - Secure defaults for all settings

2. **Secrets Management**
   - No hardcoded secrets in code
   - Support for external secrets management
   - Secure handling of configuration files

3. **Dependency Security**
   - Regular updates of dependencies
   - Vulnerability scanning
   - Minimal dependency footprint

## Authentication Implementation

### API Key Authentication Implementation

```python
class ApiKeyAuthenticator:
    def __init__(self, config):
        self.api_key = config.get('linear.auth.api_key') or os.environ.get('LINEAR_API_KEY')
        if not self.api_key:
            raise ConfigurationError("Linear API key not configured")
    
    def get_auth_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def validate(self):
        # Test API key validity with a simple query
        client = LinearClient(self.api_key)
        try:
            result = client.execute_query("{ viewer { id } }")
            return "viewer" in result and "id" in result["viewer"]
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            return False
```

### OAuth Authentication Implementation

```python
class OAuthAuthenticator:
    def __init__(self, config):
        self.client_id = config.get('linear.auth.oauth.client_id') or os.environ.get('LINEAR_OAUTH_CLIENT_ID')
        self.client_secret = config.get('linear.auth.oauth.client_secret') or os.environ.get('LINEAR_OAUTH_CLIENT_SECRET')
        self.redirect_uri = config.get('linear.auth.oauth.redirect_uri')
        self.token_store = TokenStore()
        
        if not (self.client_id and self.client_secret and self.redirect_uri):
            raise ConfigurationError("Linear OAuth configuration incomplete")
    
    def get_authorization_url(self, state):
        return f"https://linear.app/oauth/authorize?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state={state}&scope=read,write"
    
    async def exchange_code_for_token(self, code):
        # Exchange authorization code for access token
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.linear.app/oauth/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code,
                    "grant_type": "authorization_code"
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Token exchange failed: {error_text}")
                    raise AuthenticationError("Failed to exchange code for token")
                
                token_data = await response.json()
                return token_data
    
    async def refresh_token(self, refresh_token):
        # Refresh an expired access token
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.linear.app/oauth/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Token refresh failed: {error_text}")
                    raise AuthenticationError("Failed to refresh token")
                
                token_data = await response.json()
                return token_data
    
    def get_auth_headers(self, user_id):
        token = self.token_store.get_token(user_id)
        if not token:
            raise AuthenticationError("No token available for user")
        
        if self.token_is_expired(token):
            token = self.refresh_token(token["refresh_token"])
            self.token_store.store_token(user_id, token)
        
        return {
            "Authorization": f"Bearer {token['access_token']}"
        }
    
    def token_is_expired(self, token):
        # Check if token is expired or about to expire
        expires_at = token.get("created_at", 0) + token.get("expires_in", 0)
        return time.time() > (expires_at - 300)  # 5 minute buffer
```

### MCP Server Authentication Implementation

```python
class McpServerAuthenticator:
    def __init__(self, config):
        self.enabled = config.get('security.api_key') is not None
        self.api_key = config.get('security.api_key') or os.environ.get('LINEAR_MCP_API_KEY')
    
    def authenticate_request(self, request):
        if not self.enabled:
            return True
        
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return False
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return False
            
            return token == self.api_key
        except Exception:
            return False
```

## Security Best Practices

### Secure Coding Practices

1. **Input Validation**
   - Validate all input parameters against schemas
   - Use parameterized queries for GraphQL
   - Implement proper error handling for invalid inputs

2. **Output Encoding**
   - Encode all output to prevent XSS
   - Set appropriate content-type headers
   - Sanitize data before returning to clients

3. **Authentication and Authorization**
   - Implement proper authentication checks
   - Validate permissions for all operations
   - Use secure password storage if applicable

### Operational Security

1. **Logging and Monitoring**
   - Log authentication attempts and failures
   - Monitor for unusual access patterns
   - Implement alerts for security events

2. **Deployment Security**
   - Use secure deployment practices
   - Implement proper access controls
   - Regular security audits

3. **Incident Response**
   - Plan for security incidents
   - Implement proper error reporting
   - Have a process for security updates

## Conclusion

This authentication and security design provides a comprehensive approach to securing the Linear MCP server. By implementing proper authentication with Linear's API, secure client authentication, and following security best practices, the server will provide a secure platform for integrating Linear with MCP clients.

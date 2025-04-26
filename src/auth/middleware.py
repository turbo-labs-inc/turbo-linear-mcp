"""
Authentication middleware for the Linear MCP Server.

This module provides middleware for authenticating requests to the server.
"""

import re
from typing import Callable, Dict, Optional, Union

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth.access import Role, get_access_control
from src.auth.api_key import validate_api_key
from src.utils.errors import UnauthorizedError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for FastAPI.
    
    This middleware authenticates requests using API keys or tokens.
    """

    def __init__(
        self,
        app: FastAPI,
        public_paths: Optional[list[str]] = None,
        api_key_header: str = "X-API-Key",
    ):
        """
        Initialize the authentication middleware.
        
        Args:
            app: FastAPI application
            public_paths: Optional list of path patterns that don't require authentication
            api_key_header: Header name for API key
        """
        super().__init__(app)
        self.public_paths = public_paths or [
            r"^/$",
            r"^/health",
            r"^/docs",
            r"^/redoc",
            r"^/openapi.json",
        ]
        self.api_key_header = api_key_header
        logger.info("Authentication middleware initialized")

    def is_public_path(self, path: str) -> bool:
        """
        Check if a path is public (doesn't require authentication).
        
        Args:
            path: Request path
            
        Returns:
            True if the path is public, False otherwise
        """
        return any(re.match(pattern, path) for pattern in self.public_paths)

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Authenticate requests before passing them to the application.
        
        Args:
            request: HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Skip authentication for public paths
        if self.is_public_path(request.url.path):
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get(self.api_key_header)
        
        if not api_key:
            logger.warning(f"Missing API key header: {self.api_key_header}")
            return Response(
                content='{"detail":"Authentication required"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        try:
            # Validate API key
            await validate_api_key(api_key)
            
            # Set user role in request state
            # In a real implementation, you would determine the role based on the API key
            request.state.user_role = Role.USER
            
            return await call_next(request)
        
        except UnauthorizedError as e:
            logger.warning(f"Authentication failed: {e}")
            return Response(
                content=f'{{"detail":"{str(e)}"}}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return Response(
                content='{"detail":"Internal server error during authentication"}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="application/json",
            )


# API key security scheme for Swagger documentation
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_authenticated_user(
    api_key: str = Depends(api_key_header),
) -> Dict[str, Union[str, Role]]:
    """
    Dependency for getting the authenticated user.
    
    Args:
        api_key: API key from header
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    if not api_key:
        logger.warning("Missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    try:
        # Validate API key
        await validate_api_key(api_key)
        
        # In a real implementation, you would get user info based on the API key
        return {
            "role": Role.USER,
            "api_key": api_key,
        }
    
    except UnauthorizedError as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    except Exception as e:
        logger.error(f"Error during authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication",
        )


def setup_auth_middleware(app: FastAPI, public_paths: Optional[list[str]] = None) -> None:
    """
    Set up authentication middleware for a FastAPI application.
    
    Args:
        app: FastAPI application
        public_paths: Optional list of path patterns that don't require authentication
    """
    auth_middleware = AuthMiddleware(app, public_paths)
    app.add_middleware(AuthMiddleware)
    logger.info("Authentication middleware added to application")
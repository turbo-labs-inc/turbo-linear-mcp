"""
OAuth authentication support for Linear MCP Server.

This module provides functionality for OAuth authentication with Linear.
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import requests
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from src.auth.storage import CredentialStorage, CredentialType, OAuthTokenData
from src.utils.errors import UnauthorizedError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OAuthConfig(BaseModel):
    """Configuration for OAuth authentication."""

    client_id: str
    client_secret: str
    auth_url: str = "https://linear.app/oauth/authorize"
    token_url: str = "https://api.linear.app/oauth/token"
    redirect_uri: str
    scopes: List[str] = Field(default_factory=lambda: ["read"])


class OAuthTokenResponse(BaseModel):
    """Response from Linear OAuth token endpoint."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    expires_in: int
    scope: str


class OAuthManager:
    """
    Manager for OAuth authentication.
    
    This class provides functionality for handling OAuth authentication flows
    with Linear.
    """

    def __init__(self, config: OAuthConfig, credential_storage: CredentialStorage):
        """
        Initialize the OAuth manager.
        
        Args:
            config: OAuth configuration
            credential_storage: Credential storage instance
        """
        self.config = config
        self.credential_storage = credential_storage
        self.state_nonces: Dict[str, dict] = {}
        logger.info("OAuth manager initialized")

    def get_authorization_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """
        Get the URL for the OAuth authorization page.
        
        Args:
            state: Optional state parameter
            
        Returns:
            Tuple of (url, state)
        """
        # Generate state if not provided
        if not state:
            state = str(uuid.uuid4())
        
        # Store state nonce with timestamp
        self.state_nonces[state] = {
            "created_at": datetime.now(),
        }
        
        # Clean up old nonces
        self._clean_old_nonces()
        
        # Build authorization URL
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
            "response_type": "code",
        }
        
        url = f"{self.config.auth_url}?{self._build_query_params(params)}"
        
        logger.debug(f"Generated authorization URL: {url}")
        return url, state

    def _build_query_params(self, params: Dict[str, str]) -> str:
        """
        Build a query parameter string from a dictionary.
        
        Args:
            params: Dictionary of parameters
            
        Returns:
            Query parameter string
        """
        return "&".join(f"{k}={v}" for k, v in params.items())

    def _clean_old_nonces(self) -> None:
        """Clean up old state nonces to prevent memory leaks."""
        now = datetime.now()
        expire_time = timedelta(minutes=10)
        
        to_delete = []
        for state, data in self.state_nonces.items():
            if now - data["created_at"] > expire_time:
                to_delete.append(state)
        
        for state in to_delete:
            del self.state_nonces[state]

    async def handle_callback(
        self, code: str, state: str
    ) -> Dict[str, Union[str, dict]]:
        """
        Handle the callback from Linear OAuth.
        
        Args:
            code: Authorization code
            state: State parameter
            
        Returns:
            Dictionary with token information
            
        Raises:
            HTTPException: If the callback is invalid
        """
        # Verify state
        if state not in self.state_nonces:
            logger.warning(f"Invalid OAuth state: {state}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter",
            )
        
        # Exchange code for tokens
        try:
            token_data = await self._exchange_code(code)
            
            # Clean up state nonce
            del self.state_nonces[state]
            
            return {
                "access_token": token_data.access_token,
                "token_type": token_data.token_type,
                "expires_in": token_data.expires_in,
                "scope": token_data.scope,
                "user_info": await self._get_user_info(token_data.access_token),
            }
        
        except Exception as e:
            logger.error(f"Error exchanging OAuth code: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error exchanging OAuth code: {str(e)}",
            )

    async def _exchange_code(self, code: str) -> OAuthTokenResponse:
        """
        Exchange an authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code
            
        Returns:
            Token response
            
        Raises:
            Exception: If the token exchange fails
        """
        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": self.config.redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.post(
                self.config.token_url,
                json=payload,
                headers=headers,
                timeout=10,
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Error exchanging code: HTTP {response.status_code}, "
                    f"response: {response.text}"
                )
                raise Exception(f"Error exchanging code: {response.text}")
            
            token_data = response.json()
            return OAuthTokenResponse(**token_data)
        
        except requests.RequestException as e:
            logger.error(f"Request error exchanging code: {e}")
            raise Exception(f"Request error exchanging code: {str(e)}")

    async def _get_user_info(self, access_token: str) -> Dict[str, str]:
        """
        Get user information using the access token.
        
        Args:
            access_token: OAuth access token
            
        Returns:
            User information
            
        Raises:
            Exception: If the user info request fails
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        query = """
        query {
          viewer {
            id
            name
            email
          }
        }
        """
        
        try:
            response = requests.post(
                "https://api.linear.app/graphql",
                json={"query": query},
                headers=headers,
                timeout=10,
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Error getting user info: HTTP {response.status_code}, "
                    f"response: {response.text}"
                )
                raise Exception(f"Error getting user info: {response.text}")
            
            data = response.json()
            if "errors" in data:
                logger.error(f"GraphQL errors getting user info: {data['errors']}")
                raise Exception(f"GraphQL errors getting user info: {data['errors']}")
            
            return data["data"]["viewer"]
        
        except requests.RequestException as e:
            logger.error(f"Request error getting user info: {e}")
            raise Exception(f"Request error getting user info: {str(e)}")

    async def refresh_token(self, refresh_token: str) -> OAuthTokenResponse:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New token response
            
        Raises:
            Exception: If the token refresh fails
        """
        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.post(
                self.config.token_url,
                json=payload,
                headers=headers,
                timeout=10,
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Error refreshing token: HTTP {response.status_code}, "
                    f"response: {response.text}"
                )
                raise Exception(f"Error refreshing token: {response.text}")
            
            token_data = response.json()
            return OAuthTokenResponse(**token_data)
        
        except requests.RequestException as e:
            logger.error(f"Request error refreshing token: {e}")
            raise Exception(f"Request error refreshing token: {str(e)}")

    async def validate_token(self, access_token: str) -> bool:
        """
        Validate an access token with the Linear API.
        
        Args:
            access_token: Access token to validate
            
        Returns:
            True if the token is valid, False otherwise
        """
        try:
            user_info = await self._get_user_info(access_token)
            return bool(user_info)
        except Exception:
            return False

    def store_token(
        self, 
        token_response: OAuthTokenResponse,
        user_info: Dict[str, str],
    ) -> str:
        """
        Store an OAuth token in the credential storage.
        
        Args:
            token_response: Token response from Linear
            user_info: User information
            
        Returns:
            Credential ID
        """
        from src.auth.storage import Credential, CredentialMetadata
        
        credential_id = f"oauth_{user_info['id']}"
        
        # Calculate expiration time
        expires_at = None
        if token_response.expires_in:
            expires_at = datetime.now() + timedelta(seconds=token_response.expires_in)
        
        # Create token data
        token_data = OAuthTokenData(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            token_type=token_response.token_type,
            expires_at=expires_at,
        )
        
        # Create credential metadata
        metadata = CredentialMetadata(
            id=credential_id,
            name=f"Linear OAuth - {user_info['name']}",
            type=CredentialType.OAUTH_TOKEN,
            expires_at=expires_at,
            description=f"OAuth token for {user_info['email']}",
            labels={
                "user_id": user_info["id"],
                "user_name": user_info["name"],
                "user_email": user_info["email"],
                "scope": token_response.scope,
            },
        )
        
        # Create and store credential
        credential = Credential(
            metadata=metadata,
            data=token_data,
        )
        
        self.credential_storage.store(credential)
        
        logger.info(f"Stored OAuth token for user {user_info['name']} ({user_info['id']})")
        
        return credential_id


def setup_oauth_routes(
    app: FastAPI, 
    oauth_config: OAuthConfig,
    credential_storage: CredentialStorage,
) -> None:
    """
    Set up OAuth routes for a FastAPI application.
    
    Args:
        app: FastAPI application
        oauth_config: OAuth configuration
        credential_storage: Credential storage instance
    """
    oauth_manager = OAuthManager(oauth_config, credential_storage)
    router = APIRouter(tags=["OAuth"])
    
    @router.get("/oauth/authorize")
    async def authorize():
        """Redirect to Linear OAuth authorization page."""
        auth_url, state = oauth_manager.get_authorization_url()
        return RedirectResponse(auth_url)
    
    @router.get("/oauth/callback")
    async def callback(code: str, state: str):
        """Handle OAuth callback from Linear."""
        try:
            token_info = await oauth_manager.handle_callback(code, state)
            
            # Store token
            credential_id = oauth_manager.store_token(
                OAuthTokenResponse(
                    access_token=token_info["access_token"],
                    token_type=token_info["token_type"],
                    expires_in=token_info["expires_in"],
                    scope=token_info["scope"],
                ),
                token_info["user_info"],
            )
            
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Authentication successful",
                    "user": token_info["user_info"],
                }
            )
        
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"status": "error", "message": e.detail},
            )
        
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {e}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )
    
    app.include_router(router)
    logger.info("OAuth routes set up")
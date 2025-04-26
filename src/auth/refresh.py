"""
Token refresh mechanism for OAuth authentication.

This module provides functionality for automatically refreshing OAuth tokens
before they expire.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from src.auth.oauth import OAuthManager
from src.auth.storage import (
    Credential,
    CredentialMetadata,
    CredentialStorage,
    CredentialType,
    OAuthTokenData,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TokenRefreshManager:
    """
    Manager for refreshing OAuth tokens.
    
    This class provides functionality for automatically refreshing OAuth tokens
    before they expire.
    """

    def __init__(
        self,
        oauth_manager: OAuthManager,
        credential_storage: CredentialStorage,
        refresh_margin_minutes: int = 10,
    ):
        """
        Initialize the token refresh manager.
        
        Args:
            oauth_manager: OAuth manager instance
            credential_storage: Credential storage instance
            refresh_margin_minutes: Margin in minutes before expiration to refresh
        """
        self.oauth_manager = oauth_manager
        self.credential_storage = credential_storage
        self.refresh_margin = timedelta(minutes=refresh_margin_minutes)
        self.running = False
        self.refresh_task = None
        logger.info("Token refresh manager initialized")

    async def start(self) -> None:
        """Start the token refresh manager."""
        if self.running:
            logger.warning("Token refresh manager already running")
            return
        
        self.running = True
        self.refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info("Token refresh manager started")

    async def stop(self) -> None:
        """Stop the token refresh manager."""
        if not self.running:
            logger.warning("Token refresh manager not running")
            return
        
        self.running = False
        if self.refresh_task:
            self.refresh_task.cancel()
            try:
                await self.refresh_task
            except asyncio.CancelledError:
                pass
            self.refresh_task = None
        
        logger.info("Token refresh manager stopped")

    async def _refresh_loop(self) -> None:
        """Main loop for refreshing tokens."""
        while self.running:
            try:
                await self._refresh_tokens()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in token refresh loop: {e}")
                await asyncio.sleep(60)  # Retry after a minute

    async def _refresh_tokens(self) -> None:
        """Check and refresh tokens that are about to expire."""
        # Find all OAuth tokens
        oauth_credentials = self.credential_storage.find_by_type(CredentialType.OAUTH_TOKEN)
        
        for credential in oauth_credentials:
            if not isinstance(credential.data, OAuthTokenData):
                continue
            
            # Check if token is about to expire
            if (
                credential.data.expires_at 
                and credential.data.expires_at - self.refresh_margin <= datetime.now()
                and credential.data.refresh_token
            ):
                await self._refresh_token(credential)

    async def _refresh_token(self, credential: Credential) -> bool:
        """
        Refresh an OAuth token.
        
        Args:
            credential: Credential containing the token to refresh
            
        Returns:
            True if the token was refreshed successfully, False otherwise
        """
        if not isinstance(credential.data, OAuthTokenData):
            logger.error(f"Invalid credential data type: {type(credential.data)}")
            return False
        
        # Get refresh token
        refresh_token = credential.data.refresh_token
        if not refresh_token:
            logger.warning(f"No refresh token for credential {credential.metadata.id}")
            return False
        
        try:
            # Refresh the token
            token_response = await self.oauth_manager.refresh_token(refresh_token.get_secret_value())
            
            # Calculate new expiration time
            expires_at = None
            if token_response.expires_in:
                expires_at = datetime.now() + timedelta(seconds=token_response.expires_in)
            
            # Update credential data
            new_data = OAuthTokenData(
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                token_type=token_response.token_type,
                expires_at=expires_at,
            )
            
            # Update credential metadata
            new_metadata = CredentialMetadata(
                id=credential.metadata.id,
                name=credential.metadata.name,
                type=credential.metadata.type,
                created_at=credential.metadata.created_at,
                updated_at=datetime.now(),
                expires_at=expires_at,
                description=credential.metadata.description,
                labels=credential.metadata.labels,
            )
            
            # Create and store updated credential
            updated_credential = Credential(
                metadata=new_metadata,
                data=new_data,
            )
            
            self.credential_storage.store(updated_credential)
            
            logger.info(f"Refreshed OAuth token for {credential.metadata.id}")
            return True
        
        except Exception as e:
            logger.error(f"Error refreshing token for {credential.metadata.id}: {e}")
            return False


def setup_token_refresh(
    app,
    oauth_manager: OAuthManager,
    credential_storage: CredentialStorage,
) -> TokenRefreshManager:
    """
    Set up token refresh for a FastAPI application.
    
    Args:
        app: FastAPI application
        oauth_manager: OAuth manager instance
        credential_storage: Credential storage instance
        
    Returns:
        Token refresh manager instance
    """
    refresh_manager = TokenRefreshManager(oauth_manager, credential_storage)
    
    @app.on_event("startup")
    async def startup_token_refresh():
        """Start token refresh on application startup."""
        await refresh_manager.start()
    
    @app.on_event("shutdown")
    async def shutdown_token_refresh():
        """Stop token refresh on application shutdown."""
        await refresh_manager.stop()
    
    logger.info("Token refresh set up")
    return refresh_manager
"""
MCP credential handling module.

This module provides functionality for secure handling of credentials for the MCP server.
"""

import base64
import json
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel, Field, SecretStr

from src.utils.errors import UnauthorizedError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CredentialType(str, Enum):
    """Types of credentials that can be stored."""

    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    USERNAME_PASSWORD = "username_password"


class CredentialMetadata(BaseModel):
    """Metadata for a stored credential."""

    id: str
    name: str
    type: CredentialType
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)


class ApiKeyCredential(BaseModel):
    """API key credential."""

    key: SecretStr


class OAuthTokenCredential(BaseModel):
    """OAuth token credential."""

    access_token: SecretStr
    refresh_token: Optional[SecretStr] = None
    token_type: str = "Bearer"
    expires_at: Optional[str] = None


class UsernamePasswordCredential(BaseModel):
    """Username and password credential."""

    username: str
    password: SecretStr


class Credential(BaseModel):
    """Model for a stored credential."""

    metadata: CredentialMetadata
    data: Union[ApiKeyCredential, OAuthTokenCredential, UsernamePasswordCredential]


class CredentialManager:
    """
    Manager for secure storage and retrieval of credentials.
    
    This class provides functionality for storing and retrieving credentials
    securely using encryption.
    """

    def __init__(self, secret_key: Optional[str] = None, storage_path: Optional[Path] = None):
        """
        Initialize the credential manager.
        
        Args:
            secret_key: Secret key for encryption (if None, generated from environment)
            storage_path: Path to credential storage file (if None, uses default)
        """
        self.secret_key = secret_key or os.environ.get("MCP_CREDENTIAL_KEY")
        
        if not self.secret_key:
            # Generate a new secret key if none provided
            self.secret_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
            logger.warning("No credential encryption key provided, generated a new one")
        
        # Derive encryption key from secret key
        salt = b"mcp-credential-manager"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
        self.cipher = Fernet(key)
        
        # Set up storage
        self.storage_path = storage_path or Path.home() / ".mcp" / "credentials.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.credentials: Dict[str, bytes] = {}
        
        # Load existing credentials if available
        self._load_credentials()
        
        logger.info("Credential manager initialized")

    def _load_credentials(self) -> None:
        """Load credentials from storage."""
        if not self.storage_path.exists():
            logger.info(f"Credential storage file not found at {self.storage_path}")
            return
        
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                logger.error(f"Invalid credential data format in {self.storage_path}")
                return
            
            # Convert string keys to bytes
            self.credentials = {k: base64.b64decode(v) for k, v in data.items()}
            logger.info(f"Loaded {len(self.credentials)} credentials from {self.storage_path}")
        
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")

    def _save_credentials(self) -> None:
        """Save credentials to storage."""
        try:
            # Convert bytes to base64 strings for JSON storage
            data = {k: base64.b64encode(v).decode() for k, v in self.credentials.items()}
            
            with open(self.storage_path, "w") as f:
                json.dump(data, f)
            
            logger.info(f"Saved {len(self.credentials)} credentials to {self.storage_path}")
        
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")

    def store_credential(self, credential: Credential) -> None:
        """
        Store a credential securely.
        
        Args:
            credential: Credential to store
        """
        credential_id = credential.metadata.id
        
        # Serialize and encrypt the credential
        serialized = json.dumps(credential.dict(exclude_none=True))
        encrypted = self.cipher.encrypt(serialized.encode())
        
        # Store the encrypted credential
        self.credentials[credential_id] = encrypted
        self._save_credentials()
        
        logger.info(f"Stored credential with ID {credential_id}")

    def get_credential(self, credential_id: str) -> Optional[Credential]:
        """
        Retrieve a credential by ID.
        
        Args:
            credential_id: Credential ID
            
        Returns:
            Credential if found, None otherwise
        """
        if credential_id not in self.credentials:
            logger.warning(f"Credential with ID {credential_id} not found")
            return None
        
        try:
            # Decrypt and deserialize the credential
            encrypted = self.credentials[credential_id]
            decrypted = self.cipher.decrypt(encrypted)
            data = json.loads(decrypted)
            
            # Parse the credential
            return Credential.parse_obj(data)
        
        except Exception as e:
            logger.error(f"Error retrieving credential {credential_id}: {e}")
            return None

    def delete_credential(self, credential_id: str) -> bool:
        """
        Delete a credential by ID.
        
        Args:
            credential_id: Credential ID
            
        Returns:
            True if deleted, False if not found
        """
        if credential_id not in self.credentials:
            logger.warning(f"Credential with ID {credential_id} not found for deletion")
            return False
        
        # Remove the credential
        del self.credentials[credential_id]
        self._save_credentials()
        
        logger.info(f"Deleted credential with ID {credential_id}")
        return True

    def list_credentials(self) -> List[CredentialMetadata]:
        """
        List all stored credentials (metadata only).
        
        Returns:
            List of credential metadata
        """
        result = []
        
        for credential_id in self.credentials:
            credential = self.get_credential(credential_id)
            if credential:
                result.append(credential.metadata)
        
        return result

    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate an API key against stored credentials.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        for credential_id in self.credentials:
            credential = self.get_credential(credential_id)
            
            if (
                credential
                and credential.metadata.type == CredentialType.API_KEY
                and isinstance(credential.data, ApiKeyCredential)
                and credential.data.key.get_secret_value() == api_key
            ):
                return True
        
        return False


def get_credential_manager() -> CredentialManager:
    """
    Get the global credential manager instance.
    
    Returns:
        Credential manager instance
    """
    # Singleton pattern
    if not hasattr(get_credential_manager, "_instance"):
        get_credential_manager._instance = CredentialManager()
    
    return get_credential_manager._instance


def validate_api_key(api_key: str) -> None:
    """
    Validate an API key and raise an error if invalid.
    
    Args:
        api_key: API key to validate
        
    Raises:
        UnauthorizedError: If the API key is invalid
    """
    credential_manager = get_credential_manager()
    
    if not credential_manager.validate_api_key(api_key):
        logger.warning("Invalid API key provided")
        raise UnauthorizedError("Invalid API key")
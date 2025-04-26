"""
Secure credential storage module.

This module provides functionality for securely storing and retrieving credentials.
"""

import base64
import json
import os
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

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


class ApiKeyData(BaseModel):
    """Data for an API key credential."""

    key: SecretStr


class OAuthTokenData(BaseModel):
    """Data for an OAuth token credential."""

    access_token: SecretStr
    refresh_token: Optional[SecretStr] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None


class UsernamePasswordData(BaseModel):
    """Data for a username and password credential."""

    username: str
    password: SecretStr


class CredentialMetadata(BaseModel):
    """Metadata for a credential."""

    id: str
    name: str
    type: CredentialType
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    description: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)


class Credential(BaseModel):
    """Model for a stored credential."""

    metadata: CredentialMetadata
    data: Union[ApiKeyData, OAuthTokenData, UsernamePasswordData]

    def is_expired(self) -> bool:
        """
        Check if the credential is expired.
        
        Returns:
            True if the credential is expired, False otherwise
        """
        if self.metadata.expires_at is None:
            return False
        
        return datetime.now() > self.metadata.expires_at


class CredentialStorage:
    """
    Secure storage for credentials.
    
    This class provides functionality for securely storing and retrieving credentials
    using encryption.
    """

    def __init__(self, storage_path: Optional[Path] = None, encryption_key: Optional[str] = None):
        """
        Initialize the credential storage.
        
        Args:
            storage_path: Path to store encrypted credentials (default: ~/.linear-mcp/credentials)
            encryption_key: Key for encrypting credentials (default: from environment or generated)
        """
        self.storage_path = storage_path or Path.home() / ".linear-mcp" / "credentials"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get or generate encryption key
        self.encryption_key = encryption_key or os.environ.get("LINEAR_MCP_ENCRYPTION_KEY")
        if not self.encryption_key:
            self.encryption_key = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
            logger.warning("No encryption key provided, generated a new one")
        
        # Initialize encryption cipher
        self.cipher = self._create_cipher(self.encryption_key)
        
        # Initialize credential dictionary
        self.credentials: Dict[str, bytes] = {}
        
        # Load existing credentials
        self._load_credentials()
        
        logger.info(f"Credential storage initialized at {self.storage_path}")

    def _create_cipher(self, key: str) -> Fernet:
        """
        Create an encryption cipher from a key.
        
        Args:
            key: Encryption key
            
        Returns:
            Fernet cipher for encryption/decryption
        """
        # Derive a key from the provided key/passphrase
        salt = b"linear-mcp-credentials"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        # Generate a key that Fernet can use
        key_bytes = key.encode("utf-8")
        key_derived = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        
        return Fernet(key_derived)

    def _load_credentials(self) -> None:
        """Load credentials from storage."""
        if not self.storage_path.exists():
            logger.debug("Credential storage file does not exist yet")
            return
        
        try:
            # Load and decrypt credentials
            with open(self.storage_path, "rb") as f:
                encrypted_data = f.read()
            
            if not encrypted_data:
                logger.warning("Credential storage file is empty")
                return
            
            # Decrypt the outer container
            try:
                decrypted_data = self.cipher.decrypt(encrypted_data)
                credentials_data = json.loads(decrypted_data.decode("utf-8"))
                
                if not isinstance(credentials_data, dict):
                    logger.error("Invalid credential storage format")
                    return
                
                # Load each credential
                for cred_id, cred_data in credentials_data.items():
                    self.credentials[cred_id] = base64.b64decode(cred_data)
                
                logger.info(f"Loaded {len(self.credentials)} credentials from storage")
            
            except Exception as e:
                logger.error(f"Failed to decrypt credential storage: {e}")
                self.credentials = {}
        
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            self.credentials = {}

    def _save_credentials(self) -> None:
        """Save credentials to storage."""
        try:
            # Prepare credentials for storage
            credentials_data = {
                cred_id: base64.b64encode(cred_encrypted).decode("ascii")
                for cred_id, cred_encrypted in self.credentials.items()
            }
            
            # Encrypt and save
            json_data = json.dumps(credentials_data)
            encrypted_data = self.cipher.encrypt(json_data.encode("utf-8"))
            
            with open(self.storage_path, "wb") as f:
                f.write(encrypted_data)
            
            logger.info(f"Saved {len(self.credentials)} credentials to storage")
        
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def store(self, credential: Credential) -> None:
        """
        Store a credential.
        
        Args:
            credential: Credential to store
        """
        try:
            # Serialize and encrypt the credential
            json_data = credential.json(exclude_none=True)
            encrypted_data = self.cipher.encrypt(json_data.encode("utf-8"))
            
            # Store in memory
            self.credentials[credential.metadata.id] = encrypted_data
            
            # Save to disk
            self._save_credentials()
            
            logger.info(f"Stored credential: {credential.metadata.id} ({credential.metadata.name})")
        
        except Exception as e:
            logger.error(f"Failed to store credential: {e}")
            raise

    def get(self, credential_id: str) -> Optional[Credential]:
        """
        Get a credential by ID.
        
        Args:
            credential_id: Credential ID
            
        Returns:
            Credential if found and valid, None otherwise
        """
        if credential_id not in self.credentials:
            logger.debug(f"Credential not found: {credential_id}")
            return None
        
        try:
            # Decrypt and deserialize
            encrypted_data = self.credentials[credential_id]
            decrypted_data = self.cipher.decrypt(encrypted_data)
            credential = Credential.parse_raw(decrypted_data)
            
            # Check if expired
            if credential.is_expired():
                logger.warning(f"Credential is expired: {credential_id}")
                return None
            
            return credential
        
        except Exception as e:
            logger.error(f"Failed to get credential: {e}")
            return None

    def delete(self, credential_id: str) -> bool:
        """
        Delete a credential.
        
        Args:
            credential_id: Credential ID
            
        Returns:
            True if deleted, False if not found
        """
        if credential_id not in self.credentials:
            logger.debug(f"Credential not found for deletion: {credential_id}")
            return False
        
        # Remove from memory
        del self.credentials[credential_id]
        
        # Save to disk
        self._save_credentials()
        
        logger.info(f"Deleted credential: {credential_id}")
        return True

    def list(self) -> List[CredentialMetadata]:
        """
        List all stored credentials (metadata only).
        
        Returns:
            List of credential metadata
        """
        result = []
        
        for credential_id in self.credentials:
            credential = self.get(credential_id)
            if credential:
                result.append(credential.metadata)
        
        return result

    def find_by_type(self, credential_type: CredentialType) -> List[Credential]:
        """
        Find credentials by type.
        
        Args:
            credential_type: Credential type to find
            
        Returns:
            List of matching credentials
        """
        result = []
        
        for credential_id in self.credentials:
            credential = self.get(credential_id)
            if credential and credential.metadata.type == credential_type:
                result.append(credential)
        
        return result


def get_credential_storage() -> CredentialStorage:
    """
    Get the global credential storage instance.
    
    Returns:
        Credential storage instance
    """
    # Singleton pattern
    if not hasattr(get_credential_storage, "_instance"):
        get_credential_storage._instance = CredentialStorage()
    
    return get_credential_storage._instance
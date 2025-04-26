"""
Security audit logging for the Linear MCP Server.

This module provides functionality for logging security-related events.
"""

import json
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth.middleware import get_authenticated_user
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    API_ACCESS = "api_access"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    CONFIGURATION = "configuration"
    SECURITY = "security"


class AuditEventSeverity(str, Enum):
    """Severity levels for audit events."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent:
    """
    Model for security audit events.
    
    This class represents a security-related event that should be logged
    for auditing purposes.
    """

    def __init__(
        self,
        event_type: AuditEventType,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        severity: AuditEventSeverity = AuditEventSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a new audit event.
        
        Args:
            event_type: Type of event
            message: Event description
            user_id: ID of the user who triggered the event
            ip_address: IP address of the client
            resource: Resource being accessed or modified
            action: Action being performed
            severity: Event severity
            details: Additional event details
        """
        self.event_type = event_type
        self.message = message
        self.user_id = user_id
        self.ip_address = ip_address
        self.resource = resource
        self.action = action
        self.severity = severity
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event to a dictionary.
        
        Returns:
            Dictionary representation of the event
        """
        return {
            "event_type": self.event_type,
            "message": self.message,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "resource": self.resource,
            "action": self.action,
            "severity": self.severity,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """
        Convert the event to a JSON string.
        
        Returns:
            JSON string representation of the event
        """
        return json.dumps(self.to_dict())


class AuditLogger:
    """
    Logger for security audit events.
    
    This class handles logging security-related events for audit purposes.
    """

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize the audit logger.
        
        Args:
            log_file: Optional path to log file (if None, logs to standard logger)
        """
        self.log_file = log_file
        self.logger = get_logger("security.audit")
        logger.info("Audit logger initialized")

    def log_event(self, event: AuditEvent) -> None:
        """
        Log a security audit event.
        
        Args:
            event: Audit event to log
        """
        event_dict = event.to_dict()
        
        # Log to file if specified
        if self.log_file:
            try:
                with open(self.log_file, "a") as f:
                    f.write(event.to_json() + "\n")
            except Exception as e:
                logger.error(f"Failed to write to audit log file: {e}")
        
        # Log to logger
        if event.severity == AuditEventSeverity.INFO:
            self.logger.info(event.message, extra=event_dict)
        elif event.severity == AuditEventSeverity.WARNING:
            self.logger.warning(event.message, extra=event_dict)
        elif event.severity == AuditEventSeverity.ERROR:
            self.logger.error(event.message, extra=event_dict)
        elif event.severity == AuditEventSeverity.CRITICAL:
            self.logger.critical(event.message, extra=event_dict)

    def log_authentication(
        self,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an authentication event.
        
        Args:
            message: Event description
            user_id: ID of the user
            ip_address: IP address of the client
            success: Whether authentication was successful
            details: Additional event details
        """
        severity = AuditEventSeverity.INFO if success else AuditEventSeverity.WARNING
        
        event = AuditEvent(
            event_type=AuditEventType.AUTHENTICATION,
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            action="authenticate",
            severity=severity,
            details=details,
        )
        
        self.log_event(event)

    def log_authorization(
        self,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an authorization event.
        
        Args:
            message: Event description
            user_id: ID of the user
            ip_address: IP address of the client
            resource: Resource being accessed
            action: Action being performed
            success: Whether authorization was successful
            details: Additional event details
        """
        severity = AuditEventSeverity.INFO if success else AuditEventSeverity.WARNING
        
        event = AuditEvent(
            event_type=AuditEventType.AUTHORIZATION,
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            severity=severity,
            details=details,
        )
        
        self.log_event(event)

    def log_api_access(
        self,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an API access event.
        
        Args:
            message: Event description
            user_id: ID of the user
            ip_address: IP address of the client
            resource: Resource being accessed
            action: Action being performed
            details: Additional event details
        """
        event = AuditEvent(
            event_type=AuditEventType.API_ACCESS,
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            severity=AuditEventSeverity.INFO,
            details=details,
        )
        
        self.log_event(event)

    def log_data_modification(
        self,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a data modification event.
        
        Args:
            message: Event description
            user_id: ID of the user
            ip_address: IP address of the client
            resource: Resource being modified
            action: Action being performed
            details: Additional event details
        """
        event = AuditEvent(
            event_type=AuditEventType.DATA_MODIFICATION,
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            severity=AuditEventSeverity.INFO,
            details=details,
        )
        
        self.log_event(event)

    def log_security_event(
        self,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: AuditEventSeverity = AuditEventSeverity.WARNING,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a general security event.
        
        Args:
            message: Event description
            user_id: ID of the user
            ip_address: IP address of the client
            severity: Event severity
            details: Additional event details
        """
        event = AuditEvent(
            event_type=AuditEventType.SECURITY,
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            severity=severity,
            details=details,
        )
        
        self.log_event(event)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for audit logging of API requests.
    
    This middleware logs API requests for security audit purposes.
    """

    def __init__(
        self,
        app: FastAPI,
        audit_logger: AuditLogger,
        exclude_paths: Optional[List[str]] = None,
    ):
        """
        Initialize the audit middleware.
        
        Args:
            app: FastAPI application
            audit_logger: Audit logger instance
            exclude_paths: Paths to exclude from audit logging
        """
        super().__init__(app)
        self.audit_logger = audit_logger
        self.exclude_paths = set(exclude_paths or [])
        logger.info("Audit middleware initialized")

    async def dispatch(
        self, request: Request, call_next: callable
    ) -> Response:
        """
        Process a request and log it for audit purposes.
        
        Args:
            request: HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get request information
        start_time = time.time()
        method = request.method
        path = request.url.path
        ip_address = request.client.host if request.client else None
        user_id = getattr(request.state, "user_id", None)
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Log successful requests
            self.audit_logger.log_api_access(
                message=f"{method} {path} {status_code}",
                user_id=user_id,
                ip_address=ip_address,
                resource=path,
                action=method,
                details={
                    "status_code": status_code,
                    "duration": time.time() - start_time,
                    "query_params": str(request.query_params),
                    "headers": dict(request.headers),
                },
            )
            
            return response
        
        except Exception as e:
            # Log exceptions
            self.audit_logger.log_security_event(
                message=f"Exception during {method} {path}: {str(e)}",
                user_id=user_id,
                ip_address=ip_address,
                severity=AuditEventSeverity.ERROR,
                details={
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                    "query_params": str(request.query_params),
                    "headers": dict(request.headers),
                },
            )
            
            # Re-raise the exception
            raise


def get_audit_logger() -> AuditLogger:
    """
    Get the global audit logger instance.
    
    Returns:
        Audit logger instance
    """
    # Singleton pattern
    if not hasattr(get_audit_logger, "_instance"):
        get_audit_logger._instance = AuditLogger()
    
    return get_audit_logger._instance


def setup_audit_logging(
    app: FastAPI, log_file: Optional[str] = None, exclude_paths: Optional[List[str]] = None
) -> None:
    """
    Set up audit logging for a FastAPI application.
    
    Args:
        app: FastAPI application
        log_file: Path to audit log file
        exclude_paths: Paths to exclude from audit logging
    """
    audit_logger = AuditLogger(log_file=log_file)
    middleware = AuditMiddleware(app, audit_logger, exclude_paths=exclude_paths)
    app.add_middleware(AuditMiddleware, audit_logger=audit_logger, exclude_paths=exclude_paths)
    
    logger.info("Audit logging setup complete")
"""
Health check module for the Linear MCP Server.

This module provides health check functionality for monitoring server health.
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, FastAPI, Response, status
from pydantic import BaseModel

from src.utils.logging import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"


class HealthCheckResult(BaseModel):
    """Result of a health check."""

    name: str
    status: HealthStatus
    details: Optional[str] = None
    timestamp: float


class HealthResponse(BaseModel):
    """Response model for health check endpoints."""

    status: HealthStatus
    checks: Dict[str, HealthCheckResult]
    version: str
    uptime: float


class HealthCheck:
    """
    Health check manager for the MCP server.
    
    This class provides functionality for registering and executing health checks
    to monitor the health of the server and its dependencies.
    """

    def __init__(self, version: str = "0.1.0"):
        """
        Initialize the health check manager.
        
        Args:
            version: Server version
        """
        self.version = version
        self.start_time = time.time()
        self.checks: Dict[str, Callable[[], Tuple[HealthStatus, Optional[str]]]] = {}
        self.status_override: Optional[HealthStatus] = None
        logger.info("Health check manager initialized")

    def register_check(
        self, name: str, check_func: Callable[[], Tuple[HealthStatus, Optional[str]]]
    ) -> None:
        """
        Register a health check function.
        
        Args:
            name: Health check name
            check_func: Function that returns a tuple of (status, details)
        """
        self.checks[name] = check_func
        logger.debug(f"Registered health check: {name}")

    def _get_uptime(self) -> float:
        """Get server uptime in seconds."""
        return time.time() - self.start_time

    def override_status(self, status: Optional[HealthStatus]) -> None:
        """
        Override the overall health status.
        
        Args:
            status: Status to override with, or None to remove override
        """
        self.status_override = status
        if status:
            logger.info(f"Health status overridden to: {status}")
        else:
            logger.info("Health status override removed")

    def _aggregate_status(self, check_results: Dict[str, HealthCheckResult]) -> HealthStatus:
        """
        Determine the overall health status from check results.
        
        Args:
            check_results: Dictionary of check results
            
        Returns:
            Aggregated health status
        """
        if self.status_override:
            return self.status_override
        
        if not check_results:
            return HealthStatus.HEALTHY
        
        if any(result.status == HealthStatus.UNHEALTHY for result in check_results.values()):
            return HealthStatus.UNHEALTHY
        
        if any(result.status == HealthStatus.DEGRADED for result in check_results.values()):
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY

    def check_health(self) -> HealthResponse:
        """
        Execute all registered health checks and return results.
        
        Returns:
            Health check response
        """
        check_results = {}
        
        for name, check_func in self.checks.items():
            try:
                status, details = check_func()
                check_results[name] = HealthCheckResult(
                    name=name,
                    status=status,
                    details=details,
                    timestamp=time.time(),
                )
            except Exception as e:
                logger.error(f"Error executing health check '{name}': {e}")
                check_results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    details=f"Error: {str(e)}",
                    timestamp=time.time(),
                )
        
        overall_status = self._aggregate_status(check_results)
        
        return HealthResponse(
            status=overall_status,
            checks=check_results,
            version=self.version,
            uptime=self._get_uptime(),
        )


def setup_health_routes(app: FastAPI, health_check: HealthCheck) -> None:
    """
    Set up health check routes for the FastAPI application.
    
    Args:
        app: FastAPI application
        health_check: Health check manager instance
    """
    health_router = APIRouter(tags=["Health"])
    
    @health_router.get("/health")
    async def health() -> Dict[str, str]:
        """Simple health check endpoint returning basic status."""
        health_response = health_check.check_health()
        return {"status": health_response.status}
    
    @health_router.get("/health/details")
    async def health_details() -> HealthResponse:
        """Detailed health check endpoint returning all check results."""
        return health_check.check_health()
    
    @health_router.get("/health/readiness")
    async def readiness(response: Response) -> Dict[str, str]:
        """
        Readiness check endpoint for Kubernetes.
        
        Returns a 503 status code if the server is not ready to receive traffic.
        """
        health_response = health_check.check_health()
        
        if health_response.status != HealthStatus.HEALTHY:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
        return {"status": health_response.status}
    
    @health_router.get("/health/liveness")
    async def liveness(response: Response) -> Dict[str, str]:
        """
        Liveness check endpoint for Kubernetes.
        
        Returns a 503 status code if the server is unhealthy and should be restarted.
        """
        health_response = health_check.check_health()
        
        if health_response.status == HealthStatus.UNHEALTHY:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
        return {"status": health_response.status}
    
    app.include_router(health_router)
    logger.info("Health check routes set up")
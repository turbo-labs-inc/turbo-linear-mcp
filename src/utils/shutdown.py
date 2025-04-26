"""
Graceful shutdown utilities for the Linear MCP Server.

This module provides utilities for gracefully shutting down the server,
ensuring that in-flight requests are completed before termination.
"""

import asyncio
import signal
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

from src.utils.logging import get_logger

logger = get_logger(__name__)


class GracefulShutdown:
    """
    Handler for graceful server shutdown.
    
    This class ensures that in-flight requests are completed before
    shutting down the server.
    """

    def __init__(
        self,
        shutdown_timeout: int = 30,
        pre_shutdown_hooks: Optional[List[Callable[[], None]]] = None,
        post_shutdown_hooks: Optional[List[Callable[[], None]]] = None,
    ):
        """
        Initialize the graceful shutdown handler.
        
        Args:
            shutdown_timeout: Maximum time to wait for in-flight requests to complete (seconds)
            pre_shutdown_hooks: Callbacks to execute before shutdown
            post_shutdown_hooks: Callbacks to execute after shutdown
        """
        self.shutdown_timeout = shutdown_timeout
        self.pre_shutdown_hooks = pre_shutdown_hooks or []
        self.post_shutdown_hooks = post_shutdown_hooks or []
        self.active_connections = 0
        self._connection_lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._shutdown_complete_event = threading.Event()
        logger.info("Graceful shutdown handler initialized")

    def connection_started(self) -> None:
        """Register a new active connection."""
        with self._connection_lock:
            self.active_connections += 1

    def connection_finished(self) -> None:
        """Register a completed connection."""
        with self._connection_lock:
            self.active_connections -= 1
            if self.active_connections < 0:
                self.active_connections = 0

    def _get_active_connections(self) -> int:
        """Get the current number of active connections."""
        with self._connection_lock:
            return self.active_connections

    def shutdown(self) -> None:
        """
        Initiate graceful shutdown.
        
        This method will wait for active connections to complete,
        up to the configured timeout, before executing shutdown hooks.
        """
        if self._shutdown_event.is_set():
            logger.info("Shutdown already in progress")
            return
        
        self._shutdown_event.set()
        logger.info("Graceful shutdown initiated")
        
        # Execute pre-shutdown hooks
        for hook in self.pre_shutdown_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"Error executing pre-shutdown hook: {e}")
        
        # Wait for active connections to complete
        start_time = time.time()
        active_connections = self._get_active_connections()
        
        logger.info(f"Waiting for {active_connections} active connections to complete")
        while (
            active_connections > 0
            and (time.time() - start_time) < self.shutdown_timeout
        ):
            time.sleep(0.1)
            active_connections = self._get_active_connections()
        
        if active_connections > 0:
            logger.warning(
                f"Shutdown timeout reached with {active_connections} active connections"
            )
        else:
            logger.info("All connections completed, proceeding with shutdown")
        
        # Execute post-shutdown hooks
        for hook in self.post_shutdown_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"Error executing post-shutdown hook: {e}")
        
        self._shutdown_complete_event.set()
        logger.info("Graceful shutdown completed")

    def wait_for_shutdown(self) -> None:
        """Wait for shutdown to complete."""
        self._shutdown_complete_event.wait()

    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._shutdown_event.is_set()


def setup_signal_handlers(shutdown_handler: GracefulShutdown) -> None:
    """
    Set up signal handlers for graceful shutdown.
    
    Args:
        shutdown_handler: Graceful shutdown handler instance
    """
    def handle_exit_signal(sig: Any, frame: Any) -> None:
        """Handle exit signals for graceful shutdown."""
        logger.info(f"Received signal {sig}, initiating graceful shutdown")
        shutdown_handler.shutdown()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_exit_signal)
    signal.signal(signal.SIGTERM, handle_exit_signal)
    
    logger.info("Signal handlers registered for graceful shutdown")


def setup_shutdown_handlers(
    shutdown_timeout: int = 30,
    pre_shutdown_hooks: Optional[List[Callable[[], None]]] = None,
    post_shutdown_hooks: Optional[List[Callable[[], None]]] = None,
) -> GracefulShutdown:
    """
    Set up handlers for graceful shutdown.
    
    Args:
        shutdown_timeout: Maximum time to wait for in-flight requests to complete (seconds)
        pre_shutdown_hooks: Callbacks to execute before shutdown
        post_shutdown_hooks: Callbacks to execute after shutdown
        
    Returns:
        Configured GracefulShutdown instance
    """
    shutdown_handler = GracefulShutdown(
        shutdown_timeout=shutdown_timeout,
        pre_shutdown_hooks=pre_shutdown_hooks,
        post_shutdown_hooks=post_shutdown_hooks,
    )
    
    setup_signal_handlers(shutdown_handler)
    
    return shutdown_handler
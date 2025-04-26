"""
Metrics collection and monitoring for the Linear MCP Server.

This module provides utilities for collecting and reporting metrics such as
request counts, response times, and error rates.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Gauge, Histogram, Summary
from prometheus_client import start_http_server as start_prometheus_server

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MetricType(str, Enum):
    """Types of metrics that can be collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricDefinition:
    """Definition of a metric to be collected."""

    name: str
    description: str
    type: MetricType
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms


class MetricsManager:
    """
    Manager for collecting and reporting metrics.
    
    This class provides utilities for registering metrics, recording values,
    and exposing metrics for scraping by monitoring systems.
    """

    def __init__(self, namespace: str = "linear_mcp"):
        """
        Initialize the metrics manager.
        
        Args:
            namespace: Namespace for all metrics (used as prefix)
        """
        self.namespace = namespace
        self._metrics: Dict[str, Any] = {}
        self._metric_definitions: Dict[str, MetricDefinition] = {}
        logger.info(f"Metrics manager initialized with namespace '{namespace}'")

    def register_metric(self, definition: MetricDefinition) -> None:
        """
        Register a new metric for collection.
        
        Args:
            definition: Metric definition
        """
        name = f"{self.namespace}_{definition.name}"
        
        if name in self._metrics:
            logger.warning(f"Metric '{name}' already registered")
            return
        
        if definition.type == MetricType.COUNTER:
            self._metrics[name] = Counter(
                name, definition.description, definition.labels
            )
        elif definition.type == MetricType.GAUGE:
            self._metrics[name] = Gauge(
                name, definition.description, definition.labels
            )
        elif definition.type == MetricType.HISTOGRAM:
            self._metrics[name] = Histogram(
                name,
                definition.description,
                definition.labels,
                buckets=definition.buckets,
            )
        elif definition.type == MetricType.SUMMARY:
            self._metrics[name] = Summary(
                name, definition.description, definition.labels
            )
        
        self._metric_definitions[name] = definition
        logger.debug(f"Registered metric '{name}' of type {definition.type}")

    def get_metric(self, name: str) -> Any:
        """
        Get a registered metric.
        
        Args:
            name: Metric name
            
        Returns:
            Metric object
            
        Raises:
            ValueError: If the metric is not registered
        """
        full_name = f"{self.namespace}_{name}"
        if full_name not in self._metrics:
            raise ValueError(f"Metric '{full_name}' not registered")
        return self._metrics[full_name]

    def increment_counter(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Metric name
            value: Value to increment by
            labels: Label values
        """
        metric = self.get_metric(name)
        if labels:
            metric.labels(**labels).inc(value)
        else:
            metric.inc(value)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric value.
        
        Args:
            name: Metric name
            value: Gauge value
            labels: Label values
        """
        metric = self.get_metric(name)
        if labels:
            metric.labels(**labels).set(value)
        else:
            metric.set(value)

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Observe a value for a histogram metric.
        
        Args:
            name: Metric name
            value: Observed value
            labels: Label values
        """
        metric = self.get_metric(name)
        if labels:
            metric.labels(**labels).observe(value)
        else:
            metric.observe(value)

    def observe_summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Observe a value for a summary metric.
        
        Args:
            name: Metric name
            value: Observed value
            labels: Label values
        """
        metric = self.get_metric(name)
        if labels:
            metric.labels(**labels).observe(value)
        else:
            metric.observe(value)

    def setup_request_metrics(self, app: FastAPI) -> None:
        """
        Set up middleware for collecting request metrics.
        
        Args:
            app: FastAPI application
        """
        # Register request metrics
        self.register_metric(
            MetricDefinition(
                name="http_requests_total",
                description="Total HTTP requests",
                type=MetricType.COUNTER,
                labels=["method", "path", "status"],
            )
        )
        
        self.register_metric(
            MetricDefinition(
                name="http_request_duration_seconds",
                description="HTTP request duration in seconds",
                type=MetricType.HISTOGRAM,
                labels=["method", "path"],
                buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
            )
        )
        
        self.register_metric(
            MetricDefinition(
                name="http_requests_in_progress",
                description="Current number of HTTP requests in progress",
                type=MetricType.GAUGE,
                labels=["method", "path"],
            )
        )
        
        # Add middleware for collecting request metrics
        @app.middleware("http")
        async def metrics_middleware(request: Request, call_next: Callable) -> Response:
            """Middleware for collecting request metrics."""
            # Get path template if available or actual path
            path = request.url.path
            method = request.method
            
            # Track in-progress requests
            self.increment_counter(
                "http_requests_in_progress",
                labels={"method": method, "path": path},
            )
            
            # Measure request duration
            start_time = time.time()
            
            try:
                response = await call_next(request)
                status = str(response.status_code)
            except Exception as e:
                # Ensure counter is decremented even if an error occurs
                self.increment_counter(
                    "http_requests_in_progress",
                    value=-1,
                    labels={"method": method, "path": path},
                )
                # Record error as 500 status
                self.increment_counter(
                    "http_requests_total",
                    labels={"method": method, "path": path, "status": "500"},
                )
                # Re-raise the exception
                raise e
            
            # Decrement in-progress counter
            self.increment_counter(
                "http_requests_in_progress",
                value=-1,
                labels={"method": method, "path": path},
            )
            
            # Record total requests
            self.increment_counter(
                "http_requests_total",
                labels={"method": method, "path": path, "status": status},
            )
            
            # Record request duration
            request_duration = time.time() - start_time
            self.observe_histogram(
                "http_request_duration_seconds",
                value=request_duration,
                labels={"method": method, "path": path},
            )
            
            return response

    def start_metrics_server(self, port: int = 9090) -> None:
        """
        Start a metrics server for Prometheus scraping.
        
        Args:
            port: Port to listen on
        """
        start_prometheus_server(port)
        logger.info(f"Metrics server started on port {port}")


# Create a global metrics manager instance
metrics_manager = MetricsManager()


def setup_metrics(app: FastAPI, metrics_port: Optional[int] = None) -> None:
    """
    Set up metrics collection for the application.
    
    Args:
        app: FastAPI application
        metrics_port: Port for the metrics server (if None, metrics server is not started)
    """
    # Register common metrics
    metrics_manager.register_metric(
        MetricDefinition(
            name="server_info",
            description="Server information",
            type=MetricType.GAUGE,
            labels=["version", "environment"],
        )
    )
    
    metrics_manager.register_metric(
        MetricDefinition(
            name="server_uptime_seconds",
            description="Server uptime in seconds",
            type=MetricType.GAUGE,
        )
    )
    
    # Set up request metrics
    metrics_manager.setup_request_metrics(app)
    
    # Start metrics server if port specified
    if metrics_port:
        metrics_manager.start_metrics_server(metrics_port)
    
    logger.info("Metrics collection set up")
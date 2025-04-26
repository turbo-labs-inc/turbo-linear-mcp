"""
Rate limiting for the Linear MCP Server.

This module provides functionality for rate limiting API requests.
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union

from fastapi import FastAPI, HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    burst_size: int = 10
    strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW
    key_func: Optional[callable] = None
    excluded_paths: List[str] = None


class FixedWindowRateLimiter:
    """
    Fixed window rate limiter.
    
    This limiter uses fixed time windows (e.g., 1 minute) to track request counts.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize the rate limiter.
        
        Args:
            config: Rate limiter configuration
        """
        self.config = config
        self.window_size = 60  # seconds
        self.request_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        logger.info(
            f"Fixed window rate limiter initialized: "
            f"{config.requests_per_minute} requests per minute"
        )

    def is_rate_limited(self, key: str) -> Tuple[bool, Dict[str, Union[int, float]]]:
        """
        Check if a request should be rate limited.
        
        Args:
            key: Rate limit key (e.g., IP address)
            
        Returns:
            Tuple of (is_limited, rate_limit_info)
        """
        current_window = int(time.time() / self.window_size)
        
        # Clean up old windows
        cleaned_counts = {
            w: c for w, c in self.request_counts[key].items() 
            if w >= current_window - 1
        }
        self.request_counts[key] = defaultdict(int, cleaned_counts)
        
        # Current and previous window counts
        current_count = self.request_counts[key][current_window]
        
        # Check if the rate limit is exceeded
        if current_count >= self.config.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {key}: {current_count} requests in window")
            reset_time = (current_window + 1) * self.window_size
            return True, {
                "limit": self.config.requests_per_minute,
                "remaining": 0,
                "reset": reset_time,
                "retry_after": reset_time - time.time(),
            }
        
        # Increment the request count
        self.request_counts[key][current_window] += 1
        
        # Calculate remaining requests
        remaining = self.config.requests_per_minute - self.request_counts[key][current_window]
        reset_time = (current_window + 1) * self.window_size
        
        return False, {
            "limit": self.config.requests_per_minute,
            "remaining": remaining,
            "reset": reset_time,
            "retry_after": 0,
        }


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter.
    
    This limiter uses a sliding window approach to rate limiting, which provides
    smoother rate limiting behavior compared to fixed windows.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize the rate limiter.
        
        Args:
            config: Rate limiter configuration
        """
        self.config = config
        self.window_size = 60  # seconds
        self.request_timestamps: Dict[str, List[float]] = defaultdict(list)
        logger.info(
            f"Sliding window rate limiter initialized: "
            f"{config.requests_per_minute} requests per minute"
        )

    def is_rate_limited(self, key: str) -> Tuple[bool, Dict[str, Union[int, float]]]:
        """
        Check if a request should be rate limited.
        
        Args:
            key: Rate limit key (e.g., IP address)
            
        Returns:
            Tuple of (is_limited, rate_limit_info)
        """
        now = time.time()
        window_start = now - self.window_size
        
        # Remove old timestamps
        self.request_timestamps[key] = [
            ts for ts in self.request_timestamps[key] if ts > window_start
        ]
        
        # Count requests in the current window
        request_count = len(self.request_timestamps[key])
        
        # Check if the rate limit is exceeded
        if request_count >= self.config.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {key}: {request_count} requests in window")
            
            # Calculate retry after time
            if request_count > 0:
                oldest_timestamp = min(self.request_timestamps[key])
                retry_after = max(0, oldest_timestamp + self.window_size - now)
            else:
                retry_after = self.window_size
            
            return True, {
                "limit": self.config.requests_per_minute,
                "remaining": 0,
                "reset": now + retry_after,
                "retry_after": retry_after,
            }
        
        # Add the current timestamp
        self.request_timestamps[key].append(now)
        
        # Calculate remaining requests
        remaining = self.config.requests_per_minute - len(self.request_timestamps[key])
        
        # Calculate reset time
        if self.request_timestamps[key]:
            oldest_timestamp = min(self.request_timestamps[key])
            reset_time = oldest_timestamp + self.window_size
        else:
            reset_time = now + self.window_size
        
        return False, {
            "limit": self.config.requests_per_minute,
            "remaining": remaining,
            "reset": reset_time,
            "retry_after": 0,
        }


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter.
    
    This limiter implements the token bucket algorithm, which allows for burstiness
    while still enforcing a long-term rate limit.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize the rate limiter.
        
        Args:
            config: Rate limiter configuration
        """
        self.config = config
        self.refill_rate = config.requests_per_minute / 60.0  # tokens per second
        self.buckets: Dict[str, Dict[str, float]] = {}
        logger.info(
            f"Token bucket rate limiter initialized: "
            f"{config.requests_per_minute} requests per minute, "
            f"burst size: {config.burst_size}"
        )

    def is_rate_limited(self, key: str) -> Tuple[bool, Dict[str, Union[int, float]]]:
        """
        Check if a request should be rate limited.
        
        Args:
            key: Rate limit key (e.g., IP address)
            
        Returns:
            Tuple of (is_limited, rate_limit_info)
        """
        now = time.time()
        
        # Initialize bucket if needed
        if key not in self.buckets:
            self.buckets[key] = {
                "tokens": float(self.config.burst_size),
                "last_refill": now,
            }
        
        bucket = self.buckets[key]
        
        # Refill tokens
        elapsed = now - bucket["last_refill"]
        refill = elapsed * self.refill_rate
        bucket["tokens"] = min(bucket["tokens"] + refill, self.config.burst_size)
        bucket["last_refill"] = now
        
        # Check if we have enough tokens
        if bucket["tokens"] < 1.0:
            logger.warning(f"Rate limit exceeded for {key}: no tokens available")
            
            # Calculate time until next token is available
            time_until_refill = (1.0 - bucket["tokens"]) / self.refill_rate
            reset_time = now + time_until_refill
            
            return True, {
                "limit": self.config.requests_per_minute,
                "remaining": 0,
                "reset": reset_time,
                "retry_after": time_until_refill,
            }
        
        # Consume a token
        bucket["tokens"] -= 1.0
        
        # Calculate remaining tokens and reset time
        remaining = int(bucket["tokens"])
        time_until_full = (self.config.burst_size - bucket["tokens"]) / self.refill_rate
        
        return False, {
            "limit": self.config.requests_per_minute,
            "remaining": remaining,
            "reset": now + time_until_full,
            "retry_after": 0,
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests.
    
    This middleware applies rate limiting to incoming requests based on the
    configured strategy and limits.
    """

    def __init__(
        self,
        app: FastAPI,
        config: Optional[RateLimitConfig] = None,
    ):
        """
        Initialize the rate limiting middleware.
        
        Args:
            app: FastAPI application
            config: Rate limiting configuration
        """
        super().__init__(app)
        self.config = config or RateLimitConfig()
        
        # Set up the appropriate rate limiter based on the strategy
        if self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            self.limiter = FixedWindowRateLimiter(self.config)
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            self.limiter = SlidingWindowRateLimiter(self.config)
        elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            self.limiter = TokenBucketRateLimiter(self.config)
        else:
            self.limiter = FixedWindowRateLimiter(self.config)
            logger.warning(
                f"Unknown rate limit strategy: {self.config.strategy}, "
                f"using fixed window as fallback"
            )
        
        # Default key function uses IP address
        self.key_func = self.config.key_func or (
            lambda request: request.client.host if request.client else "unknown"
        )
        
        # Excluded paths
        self.excluded_paths = set(self.config.excluded_paths or [])
        
        logger.info("Rate limiting middleware initialized")

    async def dispatch(
        self, request: Request, call_next: callable
    ) -> Response:
        """
        Apply rate limiting to requests.
        
        Args:
            request: HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Get rate limit key
        rate_limit_key = self.key_func(request)
        
        # Check rate limit
        is_limited, rate_limit_info = self.limiter.is_rate_limited(rate_limit_key)
        
        # If rate limited, return 429 Too Many Requests
        if is_limited:
            return Response(
                content='{"detail":"Too many requests"}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_limit_info["remaining"]),
                    "X-RateLimit-Reset": str(int(rate_limit_info["reset"])),
                    "Retry-After": str(int(rate_limit_info["retry_after"])),
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(rate_limit_info["reset"]))
        
        return response


def setup_rate_limiting(
    app: FastAPI,
    requests_per_minute: int = 60,
    burst_size: int = 10,
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET,
    excluded_paths: Optional[List[str]] = None,
) -> None:
    """
    Set up rate limiting for a FastAPI application.
    
    Args:
        app: FastAPI application
        requests_per_minute: Maximum number of requests per minute
        burst_size: Maximum burst size for token bucket strategy
        strategy: Rate limiting strategy
        excluded_paths: Paths to exclude from rate limiting
    """
    config = RateLimitConfig(
        requests_per_minute=requests_per_minute,
        burst_size=burst_size,
        strategy=strategy,
        excluded_paths=excluded_paths or [],
    )
    
    middleware = RateLimitMiddleware(app, config)
    app.add_middleware(RateLimitMiddleware, config=config)
    
    logger.info(
        f"Rate limiting setup complete: {requests_per_minute} requests per minute, "
        f"strategy: {strategy.value}"
    )
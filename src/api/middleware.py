"""Middleware for FastAPI application.

This module implements middleware for rate limiting, request logging,
and other cross-cutting concerns.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.common.config import Config

# Initialize rate limiter
# Uses IP address as the key for rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{Config.RATE_LIMIT_REQUESTS}/{Config.RATE_LIMIT_PERIOD}"],
    storage_uri="memory://",  # Use in-memory storage (for production, consider Redis)
)


def setup_middleware(app):
    """Setup all middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Add rate limiter to app state
    app.state.limiter = limiter

    # Add rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Rate limit decorator for specific endpoints
def rate_limit(limit: str):
    """Decorator to apply custom rate limit to specific endpoints.

    Args:
        limit: Rate limit string (e.g., "5/minute", "10/hour")

    Returns:
        Decorator function
    """
    return limiter.limit(limit)

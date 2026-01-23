"""
Rate limiting configuration and middleware for API security.
"""
import redis
from typing import Optional
from urllib.parse import urlparse, urlunparse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import os
import logging

logger = logging.getLogger(__name__)

# Redis database for rate limiting (separate from main app data)
RATE_LIMIT_REDIS_DB = 1

# Rate limiting configuration
RATE_LIMITS = {
    # Authentication endpoints - strict limits
    "auth_login": "10/minute",           # OAuth login attempts
    "auth_exchange": "5/minute",         # Token exchange attempts
    "auth_refresh": "20/minute",         # Token refresh attempts
    "account_delete": "3/hour",          # Account deletion attempts (very strict)
    "admin_api_key": "5/minute",          # Admin API key attempts (strict to prevent brute force)

    # Analysis endpoints - moderate limits
    "analysis_create": "3/minute",       # Create new analysis
    "analysis_get": "100/minute",        # View analysis results
    "analysis_list": "50/minute",        # List analyses

    # Integration endpoints - strict for setup, loose for usage
    "integration_create": "5/minute",    # Add new integrations
    "integration_update": "10/minute",   # Update integration settings
    "integration_test": "10/minute",     # Test integration connection
    "integration_get": "200/minute",     # View integrations

    # Mapping endpoints - moderate limits
    "mapping_create": "20/minute",       # Create user mappings
    "mapping_update": "30/minute",       # Update mappings
    "mapping_delete": "15/minute",       # Delete mappings
    "mapping_validate": "5/minute",      # Validate GitHub mappings

    # General API endpoints
    "api_general": "1000/minute",        # General API calls
    "api_heavy": "100/minute",           # Heavy operations
}

def _ensure_redis_db(url: str, db: int = RATE_LIMIT_REDIS_DB) -> str:
    """
    Ensure the Redis URL uses the specified database number.
    Parses the URL and replaces the path with the desired database.
    """
    parsed = urlparse(url)
    # Replace path with the database number (e.g., /1)
    new_path = f"/{db}"
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        new_path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


def get_redis_storage_uri() -> Optional[str]:
    """
    Get Redis storage URI for rate limiting.
    Returns URI with database 1 to separate rate limiting data from app data.
    Returns None if Redis is not configured.
    """
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        # Ensure we use database 1 for rate limiting
        return _ensure_redis_db(redis_url, RATE_LIMIT_REDIS_DB)

    # Fallback to REDIS_HOST/REDIS_PORT
    redis_host = os.getenv("REDIS_HOST")
    if redis_host:
        try:
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
        except ValueError:
            logger.warning("Invalid REDIS_PORT value, using default 6379")
            redis_port = 6379
        return f"redis://{redis_host}:{redis_port}/{RATE_LIMIT_REDIS_DB}"

    return None


def test_redis_connection(storage_uri: str) -> bool:
    """Test if Redis is reachable at the given URI."""
    client = None
    try:
        client = redis.from_url(storage_uri, socket_timeout=5.0, socket_connect_timeout=5.0)
        client.ping()
        return True
    except Exception as e:
        logger.warning(f"⚠️  Redis not available for rate limiting: {e}")
        return False
    finally:
        if client:
            client.close()

def get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on user context.
    Priority: authenticated user > IP address
    """
    try:
        # Try to get authenticated user ID from JWT token
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # We'll enhance this to extract user ID from JWT if needed
            # For now, using IP address as fallback is secure
            pass
            
        # Check if user info is available in request state
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
            
    except Exception:
        pass
    
    # Defensive fallback to IP address with type checking
    try:
        # Ensure request is the correct type before calling get_remote_address
        if hasattr(request, 'client') and hasattr(request.client, 'host'):
            return request.client.host
        else:
            return get_remote_address(request)
    except Exception as e:
        logger.warning(f"Failed to get remote address for rate limiting: {e}")
        # Ultimate fallback
        return "unknown"

# Initialize rate limiter
_redis_storage_uri = get_redis_storage_uri()

if _redis_storage_uri and test_redis_connection(_redis_storage_uri):
    # Use Redis for distributed rate limiting (production)
    limiter = Limiter(
        key_func=get_rate_limit_key,
        storage_uri=_redis_storage_uri
    )
    logger.info(f"✅ Rate limiting using Redis storage (db={RATE_LIMIT_REDIS_DB})")
else:
    # Use in-memory storage (development/fallback)
    limiter = Limiter(key_func=get_rate_limit_key)
    logger.info("⚠️  Rate limiting using in-memory storage")

def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom rate limit exceeded response with security headers.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_key = get_rate_limit_key(request)

    # Structured logging for easier alerting and monitoring
    logger.warning(
        f"RATE_LIMIT_EXCEEDED: "
        f"path={request.url.path}, "
        f"ip={client_ip}, "
        f"key={rate_key}, "
        f"limit={getattr(exc, 'limit', 'unknown')}"
    )
    
    response = JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": f"Rate limit exceeded: {exc.detail}",
            "retry_after": exc.retry_after if hasattr(exc, 'retry_after') else 60
        }
    )
    
    # Add security headers
    response.headers["Retry-After"] = str(exc.retry_after if hasattr(exc, 'retry_after') else 60)
    response.headers["X-RateLimit-Limit"] = str(getattr(exc, 'limit', 'unknown'))
    response.headers["X-RateLimit-Remaining"] = "0"
    
    return response

# Rate limiting decorators for different endpoint types
def auth_rate_limit(endpoint_type: str = "auth_login"):
    """Rate limiter for authentication endpoints."""
    return limiter.limit(RATE_LIMITS.get(endpoint_type, "10/minute"))

def analysis_rate_limit(endpoint_type: str = "analysis_get"):
    """Rate limiter for analysis endpoints.""" 
    return limiter.limit(RATE_LIMITS.get(endpoint_type, "100/minute"))

def integration_rate_limit(endpoint_type: str = "integration_get"):
    """Rate limiter for integration endpoints."""
    return limiter.limit(RATE_LIMITS.get(endpoint_type, "200/minute"))

def mapping_rate_limit(endpoint_type: str = "mapping_create"):
    """Rate limiter for mapping endpoints."""
    return limiter.limit(RATE_LIMITS.get(endpoint_type, "20/minute"))

def general_rate_limit(endpoint_type: str = "api_general"):
    """Rate limiter for general API endpoints."""
    return limiter.limit(RATE_LIMITS.get(endpoint_type, "1000/minute"))

def heavy_rate_limit(endpoint_type: str = "api_heavy"):
    """Rate limiter for heavy/expensive operations."""
    return limiter.limit(RATE_LIMITS.get(endpoint_type, "100/minute"))

def admin_rate_limit(endpoint_type: str = "admin_api_key"):
    """Rate limiter for admin API key protected endpoints (strict to prevent brute force)."""
    return limiter.limit(RATE_LIMITS.get(endpoint_type, "5/minute"))

# Rate limiting bypass for testing/development
def bypass_rate_limiting() -> bool:
    """Check if rate limiting should be bypassed."""
    return os.getenv("BYPASS_RATE_LIMITING", "false").lower() == "true"

def conditional_rate_limit(rate_limit_func):
    """Decorator that conditionally applies rate limiting."""
    def decorator(func):
        if bypass_rate_limiting():
            logger.info("⚠️  Rate limiting bypassed for development")
            return func
        return rate_limit_func(func)
    return decorator
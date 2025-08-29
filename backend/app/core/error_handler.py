"""
Centralized error handling and retry logic for API connections.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional, TypeVar
from functools import wraps
import aiohttp
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RetryableError(Exception):
    """Exception that should trigger a retry."""
    pass

class NonRetryableError(Exception):
    """Exception that should not trigger a retry."""
    pass

class ConnectionRetryHandler:
    """Handles retries and backoff for API connections."""
    
    def __init__(
        self, 
        max_retries: int = 3, 
        initial_delay: float = 1.0, 
        backoff_multiplier: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_multiplier = backoff_multiplier
    
    async def retry_async(
        self, 
        func: Callable[..., Any], 
        *args, 
        error_context: str = "operation",
        **kwargs
    ) -> Any:
        """Retry an async function with exponential backoff."""
        last_exception = None
        delay = self.initial_delay
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                
                # Determine if error is retryable
                is_retryable = (
                    "timeout" in error_msg or
                    "connection" in error_msg or
                    "ssl" in error_msg or
                    "network" in error_msg or
                    "server disconnected" in error_msg or
                    "cannot connect to host" in error_msg
                )
                
                if not is_retryable or attempt >= self.max_retries:
                    # Log final failure
                    if attempt >= self.max_retries:
                        logger.warning(
                            f"{error_context} failed after {self.max_retries} retries: {str(e)[:100]}..."
                        )
                    else:
                        logger.error(f"{error_context} failed (non-retryable): {str(e)[:100]}...")
                    raise e
                
                # Log retry attempt
                logger.info(
                    f"{error_context} failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"retrying in {delay:.1f}s: {str(e)[:50]}..."
                )
                
                await asyncio.sleep(delay)
                delay *= self.backoff_multiplier
        
        # Should never reach here, but just in case
        raise last_exception

def with_retry(
    max_retries: int = 3, 
    initial_delay: float = 1.0, 
    backoff_multiplier: float = 2.0,
    error_context: str = "operation"
):
    """Decorator to add retry logic to async functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_handler = ConnectionRetryHandler(
                max_retries=max_retries,
                initial_delay=initial_delay, 
                backoff_multiplier=backoff_multiplier
            )
            return await retry_handler.retry_async(
                func, *args, error_context=error_context, **kwargs
            )
        return wrapper
    return decorator

class ErrorSuppressor:
    """Suppresses non-critical errors to reduce log noise."""
    
    def __init__(self, suppress_duration_minutes: int = 30):
        self.suppress_duration = timedelta(minutes=suppress_duration_minutes)
        self.last_logged: Dict[str, datetime] = {}
    
    def should_log_error(self, error_key: str) -> bool:
        """Check if error should be logged based on suppression rules."""
        now = datetime.now()
        
        if error_key in self.last_logged:
            time_since_last = now - self.last_logged[error_key]
            if time_since_last < self.suppress_duration:
                return False
        
        self.last_logged[error_key] = now
        return True
    
    def log_suppressed_error(self, logger_obj, level: str, error_key: str, message: str):
        """Log error only if not suppressed."""
        if self.should_log_error(error_key):
            log_func = getattr(logger_obj, level.lower())
            log_func(f"{message} (suppressing similar errors for {self.suppress_duration.total_seconds()/60:.0f}min)")

# Global error suppressor instance
error_suppressor = ErrorSuppressor()

class APIConnectionManager:
    """Manages API connections with proper error handling and cleanup."""
    
    @staticmethod
    def get_http_session(timeout_seconds: int = 30) -> aiohttp.ClientSession:
        """Create an HTTP session with proper timeout and error handling."""
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        
        # Create connector with SSL verification and connection limits
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=10,  # Connections per host
            ttl_dns_cache=300,  # DNS cache TTL (5 minutes)
            use_dns_cache=True,
            ssl=True  # Enable SSL verification
        )
        
        return aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            raise_for_status=False  # Don't raise exceptions for HTTP errors
        )
    
    @staticmethod 
    @with_retry(max_retries=2, initial_delay=1.0, error_context="API connection test")
    async def test_api_connection(
        url: str, 
        headers: Dict[str, str], 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Test API connection with retry logic."""
        async with APIConnectionManager.get_http_session(timeout_seconds=15) as session:
            async with session.get(url, headers=headers, params=params or {}) as response:
                if response.status == 200:
                    return {"success": True, "status": response.status}
                else:
                    error_text = await response.text()
                    return {
                        "success": False, 
                        "status": response.status, 
                        "error": f"HTTP {response.status}: {error_text[:200]}"
                    }

def categorize_error(error: Exception) -> Dict[str, Any]:
    """Categorize errors for better handling and logging."""
    error_msg = str(error).lower()
    error_type = type(error).__name__
    
    categories = {
        "network": [
            "cannot connect to host", "connection refused", "connection reset", 
            "network is unreachable", "server disconnected", "ssl"
        ],
        "timeout": ["timeout", "timed out"],
        "authentication": ["unauthorized", "forbidden", "invalid token", "authentication"],
        "rate_limit": ["rate limit", "too many requests"],
        "database": ["pool", "database", "connection timed out", "sqlalchemy"],
        "api_error": ["bad request", "not found", "internal server error"]
    }
    
    category = "unknown"
    for cat, keywords in categories.items():
        if any(keyword in error_msg for keyword in keywords):
            category = cat
            break
    
    severity = "error"
    if category in ["network", "timeout"]:
        severity = "warning"  # These are often temporary
    elif category in ["rate_limit"]:
        severity = "info"  # Expected behavior
    
    return {
        "category": category,
        "severity": severity,
        "error_type": error_type,
        "retryable": category in ["network", "timeout", "rate_limit"]
    }
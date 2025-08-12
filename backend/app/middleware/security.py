"""
Security middleware for request validation and response headers.
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import json

from ..core.input_validation import validate_request_size, sanitize_dict_recursive

logger = logging.getLogger(__name__)

# Security configuration
SECURITY_HEADERS = {
    # Content Security Policy - prevent XSS attacks (HARDENED)
    "Content-Security-Policy": (
        "default-src 'none'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https:; "
        "connect-src 'self' https:; "
        "media-src 'none'; "
        "object-src 'none'; "
        "child-src 'none'; "
        "worker-src 'none'; "
        "form-action 'self'; "
        "base-uri 'self'; "
        "manifest-src 'self'; "
        "frame-ancestors 'none'"
    ),
    
    # Prevent clickjacking attacks
    "X-Frame-Options": "DENY",
    
    # Prevent MIME type sniffing
    "X-Content-Type-Options": "nosniff",
    
    # Enable XSS protection in browsers
    "X-XSS-Protection": "1; mode=block",
    
    # Only send referrer for same-origin requests
    "Referrer-Policy": "same-origin",
    
    # Prevent caching of sensitive responses
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
    
    # Remove server information
    "Server": "API",
    
    # Permissions policy (formerly Feature-Policy)
    "Permissions-Policy": (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "accelerometer=(), "
        "gyroscope=()"
    )
}

# Routes that should allow caching (static content, public data)
CACHEABLE_ROUTES = [
    "/health",
    "/",
    "/docs",
    "/openapi.json"
]

# Routes that contain sensitive data (never cache)
SENSITIVE_ROUTES = [
    "/auth/",
    "/analysis/",
    "/analyses/",
    "/integrations/",
    "/mappings/"
]

async def security_middleware(request: Request, call_next: Callable) -> Response:
    """
    Security middleware to validate requests and add security headers.
    """
    start_time = time.time()
    
    try:
        # 1. Request size validation - HARDENED
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                content_length_int = int(content_length)
                if not validate_request_size(content_length_int):
                    logger.warning(f"🚨 Request too large: {content_length} bytes from {request.client.host}")
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": "request_too_large",
                            "detail": "Request size exceeds maximum allowed limit",
                            "max_size": "10MB"
                        }
                    )
            except ValueError:
                logger.warning(f"🚨 Invalid Content-Length header: {content_length} from {request.client.host}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "invalid_content_length",
                        "detail": "Invalid Content-Length header"
                    }
                )
        
        # Request size validation relies on Content-Length header
        # Body reading would consume the request stream and break downstream processing
        
        # 2. Request method validation
        if request.method not in ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]:
            logger.warning(f"🚨 Invalid HTTP method: {request.method} from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                content={
                    "error": "method_not_allowed", 
                    "detail": f"HTTP method {request.method} not allowed"
                }
            )
        
        # 3. Content-Type validation for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").lower()
            if content_type and not any(allowed in content_type for allowed in [
                "application/json",
                "application/x-www-form-urlencoded", 
                "multipart/form-data",
                "text/plain"
            ]):
                logger.warning(f"🚨 Invalid content-type: {content_type} from {request.client.host}")
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={
                        "error": "unsupported_media_type",
                        "detail": "Content-Type not supported"
                    }
                )
        
        # 4. Process the request
        response = await call_next(request)
        
        # 5. Add security headers to response
        for header, value in SECURITY_HEADERS.items():
            # Don't override caching for cacheable routes
            if header in ["Cache-Control", "Pragma", "Expires"]:
                if any(route in str(request.url.path) for route in CACHEABLE_ROUTES):
                    continue
                    
                # Force no-cache for sensitive routes
                if any(route in str(request.url.path) for route in SENSITIVE_ROUTES):
                    response.headers[header] = value
            else:
                response.headers[header] = value
        
        # 6. Add custom security headers based on route
        request_path = str(request.url.path)
        
        # API endpoints get additional security
        if request_path.startswith("/auth/") or request_path.startswith("/api/"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow, nosnippet, noarchive"
        
        # Add processing time header (for monitoring)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log security events
        if response.status_code >= 400:
            logger.info(f"🛡️  Security response: {response.status_code} for {request.method} {request_path}")
        
        return response
        
    except Exception as e:
        # Log security middleware errors
        logger.error(f"🚨 Security middleware error: {e}")
        
        # Return secure error response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "detail": "An internal error occurred"
            },
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY"
            }
        )

# Request sanitization is handled by Pydantic validation models
# This eliminates the need for middleware-level body manipulation that can break request handling

def add_security_headers(response: Response, request: Request) -> Response:
    """
    Utility function to add security headers to any response.
    """
    request_path = str(request.url.path)
    
    # Add basic security headers
    response.headers.update({
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY", 
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "same-origin"
    })
    
    # Add CSP for API endpoints
    if request_path.startswith("/api/") or request_path.startswith("/auth/"):
        response.headers["Content-Security-Policy"] = "default-src 'none'"
    
    # Prevent caching of sensitive endpoints
    if any(sensitive in request_path for sensitive in SENSITIVE_ROUTES):
        response.headers.update({
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache", 
            "Expires": "0"
        })
    
    return response

# IP-based rate limiting helpers
def is_suspicious_ip(ip: str) -> bool:
    """
    Check if IP address looks suspicious.
    """
    # Private/local IPs are generally safe
    private_ranges = [
        "127.0.0.1",
        "10.",
        "192.168.",
        "172."
    ]
    
    if any(ip.startswith(range_start) for range_start in private_ranges):
        return False
    
    # Add your suspicious IP detection logic here
    # For example, check against threat intelligence feeds
    
    return False

def log_security_event(event_type: str, request: Request, details: dict = None):
    """
    Log security events for monitoring.
    """
    event_data = {
        "event_type": event_type,
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "method": request.method,
        "path": str(request.url.path),
        "timestamp": time.time()
    }
    
    if details:
        event_data.update(details)
    
    logger.warning(f"🚨 Security Event: {json.dumps(event_data)}")

# Export middleware functions
__all__ = [
    'security_middleware',
    'add_security_headers',
    'log_security_event',
    'is_suspicious_ip'
]
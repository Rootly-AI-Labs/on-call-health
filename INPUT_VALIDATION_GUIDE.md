# 🛡️ Input Validation & Security Implementation Guide

## Overview

We've implemented comprehensive input validation and sanitization to protect the API from injection attacks, XSS, and other security vulnerabilities. The system uses **Pydantic models** with custom validators and security middleware.

## 🎯 Security Features Implemented

### 1. **Input Sanitization**
- **HTML Escape**: Prevents XSS attacks by escaping HTML characters
- **URL Decode**: Normalizes input to detect encoded attacks
- **Control Character Removal**: Strips null bytes and control characters
- **Whitespace Normalization**: Prevents excessive whitespace attacks

### 2. **Injection Prevention**
- **SQL Injection**: Detects and blocks SQL keywords and patterns
- **Command Injection**: Prevents shell command execution attempts
- **Script Injection**: Blocks JavaScript and other script execution
- **Directory Traversal**: Prevents file system access attempts

### 3. **API Token Security**
- **Format Validation**: Enforces correct token formats per platform
- **Character Restriction**: Only allows safe characters in tokens
- **Length Validation**: Enforces minimum and maximum token lengths
- **Platform-Specific Rules**: Different validation rules per API provider

### 4. **Request Size Limits**
- **Total Request Size**: 10MB maximum per request
- **String Length**: Configurable maximum string lengths
- **Array Length**: Maximum 1000 items per array
- **Dictionary Size**: Maximum 100 keys per dictionary

### 5. **Security Headers**
- **Content Security Policy (CSP)**: Prevents XSS attacks
- **X-Frame-Options**: Prevents clickjacking attacks
- **X-Content-Type-Options**: Prevents MIME sniffing
- **X-XSS-Protection**: Enables browser XSS protection
- **Cache Control**: Prevents sensitive data caching

## 🏗️ Implementation Architecture

### Core Components

#### 1. **Input Validation Module** (`app/core/input_validation.py`)
```python
from app.core.input_validation import (
    BaseValidatedModel,
    RootlyTokenRequest,
    GitHubTokenRequest,
    AnalysisRequest,
    UserMappingRequest
)
```

#### 2. **Security Middleware** (`app/middleware/security.py`)
- Automatic request validation
- Security headers injection
- Request size enforcement
- Content-type validation

#### 3. **Validation Models**
```python
class RootlyTokenRequest(BaseValidatedModel):
    token: str = Field(..., min_length=10, max_length=500)
    
    @validator('token')
    def validate_token_format(cls, v):
        if not validate_token_format("rootly", v):
            raise ValueError("Invalid Rootly token format")
        return v
```

## 📋 Validation Models by Category

### Authentication Models
```python
# OAuth login validation
class OAuthLoginRequest(BaseValidatedModel):
    redirect_origin: Optional[str] = Field(None, max_length=500)
    
    @validator('redirect_origin')
    def validate_redirect_origin(cls, v):
        # Only allow whitelisted origins
        safe_origins = ["http://localhost:3000", settings.FRONTEND_URL]
        if v not in safe_origins:
            raise ValueError("Redirect origin not allowed")
        return v

# Token exchange validation  
class TokenExchangeRequest(BaseValidatedModel):
    code: str = Field(..., min_length=10, max_length=500)
    
    @validator('code')
    def validate_auth_code(cls, v):
        # Must be URL-safe base64 only
        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError("Invalid authorization code format")
        return v
```

### Integration Models
```python
# Rootly integration validation
class RootlyIntegrationRequest(BaseValidatedModel):
    name: str = Field(..., min_length=1, max_length=100)
    token: str = Field(..., description="Rootly API token")
    organization_domain: Optional[str] = Field(None, max_length=255)
    
    @validator('token')
    def validate_token(cls, v):
        if not validate_token_format("rootly", v):
            raise ValueError("Invalid Rootly token format")
        return v
    
    @validator('organization_domain')
    def validate_domain(cls, v):
        if v and not PATTERNS["domain"].match(v):
            raise ValueError("Invalid domain format")
        return v

# GitHub integration validation
class GitHubIntegrationRequest(BaseValidatedModel):
    token: str = Field(..., description="GitHub personal access token")
    organization: Optional[str] = Field(None, max_length=100)
    
    @validator('token')
    def validate_token(cls, v):
        # Must start with ghp_, gho_, ghu_, ghs_, or ghr_
        if not validate_token_format("github", v):
            raise ValueError("Invalid GitHub token format")
        return v
```

### Analysis Models
```python
# Burnout analysis request
class AnalysisRequest(BaseValidatedModel):
    integration_id: int = Field(..., gt=0)
    time_range: int = Field(30, gt=0, le=365)
    include_weekends: bool = Field(True)
    include_github: bool = Field(False)
    include_slack: bool = Field(False)
    enable_ai: bool = Field(False)
    
    @validator('time_range')
    def validate_time_range(cls, v):
        allowed_ranges = [7, 14, 30, 60, 90, 180, 365]
        if v not in allowed_ranges:
            raise ValueError(f"Time range must be one of: {allowed_ranges}")
        return v
```

### User Mapping Models
```python
# User mapping validation
class UserMappingRequest(BaseValidatedModel):
    source_platform: PlatformType = Field(..., description="Source platform")
    source_identifier: EmailStr = Field(..., description="Source email")
    target_platform: PlatformType = Field(..., description="Target platform")
    target_identifier: str = Field(..., min_length=1, max_length=100)
    
    @validator('target_identifier')
    def validate_target_identifier(cls, v, values):
        target_platform = values.get('target_platform')
        
        if target_platform == 'github':
            if not PATTERNS["github_username"].match(v):
                raise ValueError("Invalid GitHub username format")
        elif target_platform == 'slack':
            if not (PATTERNS["slack_user_id"].match(v) or '@' in v):
                raise ValueError("Invalid Slack user identifier format")
        
        return v
```

## 🔧 Token Format Validation

### Supported Token Formats

#### Rootly Tokens
```python
Pattern: ^[A-Za-z0-9_-]{20,100}$
Example: rootly_abc123def456ghi789jkl012
```

#### GitHub Tokens
```python
Pattern: ^(ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9]{36,255}$
Examples: 
  - ghp_1234567890abcdef1234567890abcdef12345678  # Personal access token
  - gho_1234567890abcdef1234567890abcdef12345678  # OAuth token
  - ghu_1234567890abcdef1234567890abcdef12345678  # User-to-server token
```

#### Anthropic Tokens
```python
Pattern: ^sk-ant-[A-Za-z0-9-_]{20,200}$
Format: Long alphanumeric tokens with specific prefix
```

#### OpenAI Tokens
```python
Pattern: ^sk-[A-Za-z0-9]{48}$
Format: Fixed-length alphanumeric tokens with sk- prefix
```

## 🛠️ Usage Examples

### In Endpoint Implementation
```python
from app.core.input_validation import RootlyTokenRequest
from app.core.rate_limiting import integration_rate_limit

@router.post("/token/test")
@integration_rate_limit("integration_test")
async def test_rootly_token(
    request: Request,
    token_request: RootlyTokenRequest,  # ✅ Automatic validation
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # token_request.token is already validated and sanitized
    client = RootlyAPIClient(token_request.token)
    return await client.test_connection()
```

### Manual Validation
```python
from app.core.input_validation import validate_token_format, sanitize_string

# Validate token format
if not validate_token_format("github", user_token):
    raise HTTPException(400, "Invalid GitHub token format")

# Sanitize user input
safe_name = sanitize_string(user_input, max_length=100)
```

### Custom Validation
```python
from app.core.input_validation import BaseValidatedModel
from pydantic import validator, Field

class CustomRequest(BaseValidatedModel):
    email: EmailStr = Field(..., description="User email")
    custom_field: str = Field(..., min_length=1, max_length=50)
    
    @validator('custom_field')
    def validate_custom(cls, v):
        # Custom validation logic
        if "forbidden" in v.lower():
            raise ValueError("Field contains forbidden content")
        return v
```

## 🧪 Testing Input Validation

### Automated Testing
```bash
cd backend
python test_input_validation.py
```

### Manual Testing Examples

#### Test SQL Injection Protection
```bash
curl -X POST "http://localhost:8000/rootly/token/test" \
  -H "Content-Type: application/json" \
  -d '{"token": "test'\'' OR 1=1; --"}'

# Expected: 400 Bad Request with validation error
```

#### Test XSS Protection
```bash
curl -X POST "http://localhost:8000/rootly/token/test" \
  -H "Content-Type: application/json" \
  -d '{"name": "<script>alert(\"xss\")</script>"}'

# Expected: 400 Bad Request - malicious content detected
```

#### Test Token Format Validation
```bash
curl -X POST "http://localhost:8000/rootly/token/test" \
  -H "Content-Type: application/json" \
  -d '{"token": "invalid_token_format!@#$"}'

# Expected: 422 Unprocessable Entity - invalid token format
```

#### Test Request Size Limits
```bash
# Create a large payload (>10MB)
python -c "
import json
import requests
payload = {'data': 'A' * (11 * 1024 * 1024)}  # 11MB
response = requests.post('http://localhost:8000/rootly/token/test', json=payload)
print(f'Status: {response.status_code}')  # Expected: 413 Request Entity Too Large
"
```

## 🔍 Security Headers

### Automatic Headers (All Responses)
```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' ...
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: same-origin
Server: API
```

### Sensitive Route Headers
```http
Cache-Control: no-cache, no-store, must-revalidate
Pragma: no-cache
Expires: 0
X-Robots-Tag: noindex, nofollow, nosnippet, noarchive
```

## 🚨 Error Handling

### Validation Error Response Format
```json
{
  "detail": [
    {
      "loc": ["body", "token"],
      "msg": "Invalid Rootly token format",
      "type": "value_error"
    }
  ]
}
```

### Security Error Response Format
```json
{
  "error": "validation_error",
  "detail": "Input contains potentially dangerous content",
  "field": "name"
}
```

### Request Size Error Response
```json
{
  "error": "request_too_large", 
  "detail": "Request size exceeds maximum allowed limit",
  "max_size": "10MB"
}
```

## 📊 Monitoring & Logging

### Security Event Logging
```python
# Automatic logging of security events
logger.warning(f"🚨 Potential injection detected in input: {pattern}")
logger.warning(f"🚨 Request too large: {content_length} bytes from {ip}")
logger.warning(f"🚨 Invalid token format submitted for {platform}")
```

### Monitoring Metrics
```python
# Key metrics to monitor:
- validation_errors_total
- security_blocks_total  
- oversized_requests_total
- malicious_content_detected_total
- token_format_errors_total
```

## ⚙️ Configuration

### Environment Variables
```bash
# Maximum request size (default: 10MB)
MAX_REQUEST_SIZE_MB=10

# String validation limits
MAX_STRING_LENGTH=10000
MAX_LIST_LENGTH=1000
MAX_DICT_KEYS=100

# Security features toggles
ENABLE_INPUT_SANITIZATION=true
ENABLE_INJECTION_DETECTION=true
ENABLE_SECURITY_HEADERS=true
```

### Custom Validation Patterns
```python
# In input_validation.py - add custom patterns
PATTERNS = {
    "custom_id": re.compile(r"^CID_[A-Za-z0-9]{8}$"),
    "safe_filename": re.compile(r"^[a-zA-Z0-9._-]{1,255}$"),
    # ... other patterns
}
```

## 🛡️ Security Best Practices

### 1. **Always Use Validation Models**
```python
# ✅ GOOD - Uses validation model
async def create_integration(request: RootlyIntegrationRequest):
    # Automatic validation and sanitization
    pass

# ❌ BAD - No validation
async def create_integration(name: str, token: str):
    # Raw input - potential security risk
    pass
```

### 2. **Validate at Multiple Levels**
```python
# Layer 1: Pydantic model validation
class TokenRequest(BaseValidatedModel):
    token: str = Field(..., min_length=10)

# Layer 2: Custom business logic validation  
@validator('token')
def validate_business_rules(cls, v):
    if not is_token_active(v):
        raise ValueError("Token is inactive")
    return v

# Layer 3: Runtime validation
async def use_token(token: str):
    if not await verify_token_permissions(token):
        raise HTTPException(403, "Insufficient permissions")
```

### 3. **Sanitize Output**
```python
# Always sanitize data going to external systems
sanitized_data = sanitize_dict_recursive(user_data)
await external_api.send(sanitized_data)
```

### 4. **Log Security Events**
```python
from app.middleware.security import log_security_event

log_security_event("injection_attempt", request, {
    "pattern": detected_pattern,
    "input": suspicious_input[:100]  # Truncated for logs
})
```

## 🚀 Production Deployment

### Deployment Checklist
- [ ] All endpoints use validation models
- [ ] Security middleware enabled
- [ ] Request size limits configured
- [ ] Security headers verified
- [ ] Input validation tests passing
- [ ] Security event logging configured
- [ ] Monitoring and alerting set up

### Railway Environment Variables
```bash
railway variables set ENABLE_INPUT_SANITIZATION=true
railway variables set ENABLE_INJECTION_DETECTION=true
railway variables set MAX_REQUEST_SIZE_MB=10
```

## 🆘 Troubleshooting

### Common Issues

**1. "Validation error: Input contains dangerous content"**
```python
# Check if input contains SQL/script injection patterns
# Review the sanitize_string function for allowed characters
```

**2. "Token format validation failed"**  
```python
# Verify token matches expected format in PATTERNS dict
# Check if token has correct prefix for each platform
```

**3. "Request entity too large"**
```python
# Check request size is under 10MB limit
# Consider breaking large requests into smaller chunks
```

### Debug Mode
```python
# Enable detailed validation logging
import logging
logging.getLogger("app.core.input_validation").setLevel(logging.DEBUG)
```

---

## 📞 Support

For input validation issues:
1. Check validation model requirements
2. Review security event logs
3. Test with validation test suite
4. Check request size and format
5. Contact security team for complex validation needs
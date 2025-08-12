# 🔐 Rate Limiting Implementation Guide

## Overview

We've implemented comprehensive rate limiting to protect the API from abuse and ensure fair usage. The system uses **slowapi** with Redis for distributed rate limiting in production.

## 🎯 Rate Limits by Endpoint Category

### Authentication Endpoints (Strict)
- **OAuth Login**: `10/minute` - Prevents brute force attacks
- **Token Exchange**: `5/minute` - Critical security endpoint
- **Token Refresh**: `20/minute` - Allow reasonable refresh frequency

### Analysis Endpoints (Moderate)
- **Create Analysis**: `3/minute` - Expensive operations
- **View Analysis**: `100/minute` - High read capacity
- **List Analyses**: `50/minute` - Reasonable browsing

### Integration Endpoints (Variable)
- **Create Integration**: `5/minute` - Setup operations
- **Update Integration**: `10/minute` - Configuration changes
- **Test Integration**: `10/minute` - Connection testing
- **View Integrations**: `200/minute` - High read capacity

### Mapping Endpoints (Moderate)
- **Create Mappings**: `20/minute` - Bulk operations allowed
- **Update Mappings**: `30/minute` - Edit operations
- **Delete Mappings**: `15/minute` - Destructive operations
- **Validate Mappings**: `5/minute` - API-intensive validation

## 🏗️ Architecture

### Development Mode
- **Storage**: In-memory (no Redis required)
- **Key Function**: IP address + user ID (if authenticated)
- **Bypass**: Set `BYPASS_RATE_LIMITING=true` for testing

### Production Mode
- **Storage**: Redis for distributed rate limiting
- **Key Function**: Authenticated user ID (preferred) → IP address (fallback)
- **High Availability**: Redis persistence and clustering support

## ⚙️ Configuration

### Environment Variables

```bash
# Rate Limiting Configuration
REDIS_URL=redis://localhost:6379/1              # Production Redis
REDIS_HOST=localhost                            # Redis host
REDIS_PORT=6379                                # Redis port  
REDIS_DB=1                                     # Rate limiting database
BYPASS_RATE_LIMITING=false                     # Disable for production

# Token Security
ENCRYPTION_KEY=your-fernet-key-here            # For API token encryption
```

### Railway Production Setup

1. **Add Redis Add-on**:
   ```bash
   railway add redis
   ```

2. **Set Environment Variables**:
   ```bash
   railway variables set BYPASS_RATE_LIMITING=false
   railway variables set REDIS_URL=$REDIS_URL  # Auto-populated by Railway
   ```

3. **Deploy**:
   ```bash
   railway deploy
   ```

## 🧪 Testing Rate Limiting

### Automated Testing
```bash
cd backend
python test_rate_limiting.py
```

This script will:
- Test authentication endpoint limits
- Verify rate limit headers
- Test rate limit recovery
- Validate error responses

### Manual Testing
```bash
# Test OAuth endpoint (should limit after 10 requests)
for i in {1..15}; do
  curl -i "http://localhost:8000/auth/google" 
  echo "Request $i completed"
done
```

### Expected Response When Rate Limited
```json
{
  "error": "rate_limit_exceeded",
  "detail": "Rate limit exceeded: 10 per 1 minute",
  "retry_after": 60
}
```

**Headers**:
- `Retry-After: 60`
- `X-RateLimit-Limit: 10`
- `X-RateLimit-Remaining: 0`

## 🔍 Monitoring & Logging

### Rate Limit Events
- **Logged**: Every rate limit exceeded event
- **Format**: `🚨 Rate limit exceeded for {user/ip} on {endpoint}`
- **Level**: WARNING

### Production Monitoring
```python
# Add to your monitoring dashboard
rate_limit_exceeded_count = count(log_entries.level == "WARNING" and "Rate limit exceeded" in log_entries.message)
```

### Alerting Thresholds
- **High Usage**: >100 rate limit events/hour
- **Potential Attack**: >1000 rate limit events/hour
- **Service Impact**: Rate limiting errors >5% of total requests

## 🚨 Security Features

### Attack Prevention
- **Brute Force**: OAuth login limits prevent credential attacks
- **DDoS**: Per-IP limits prevent overwhelming the service
- **API Abuse**: Per-user limits prevent individual account abuse

### Response Security
- **No Info Leakage**: Rate limit responses don't reveal system architecture
- **Consistent Timing**: All rate-limited responses have consistent delays
- **Header Security**: Rate limit headers help legitimate clients

## 🛠️ Troubleshooting

### Common Issues

**1. "Redis connection failed"**
```bash
# Check Redis is running
redis-cli ping
# Should return PONG

# Check Redis URL format
echo $REDIS_URL
# Should be: redis://host:port/db
```

**2. "Rate limiting bypassed in production"**
```bash
# Check environment variable
echo $BYPASS_RATE_LIMITING
# Should be: false (or unset)

# Check logs for bypass warnings
grep "Rate limiting bypassed" logs/
```

**3. "Rate limits too strict/loose"**
- Edit limits in `backend/app/core/rate_limiting.py`
- Restart application for changes to take effect
- Monitor usage patterns and adjust accordingly

### Development Debugging
```bash
# Enable rate limiting bypass for testing
export BYPASS_RATE_LIMITING=true

# Check rate limiting configuration
python -c "
from app.core.rate_limiting import RATE_LIMITS
import json
print(json.dumps(RATE_LIMITS, indent=2))
"
```

## 🔄 Future Enhancements

### Planned Improvements
1. **Dynamic Rate Limits**: Adjust limits based on system load
2. **User Tiers**: Different limits for different user types
3. **Geographic Limits**: Location-based rate limiting
4. **Behavior Analysis**: ML-based abuse detection

### Advanced Configuration
```python
# Custom rate limit key function
def advanced_rate_limit_key(request: Request) -> str:
    # Consider user tier, geographic location, time of day
    user_tier = get_user_tier(request)
    if user_tier == "premium":
        return f"premium:{get_user_id(request)}"
    return get_remote_address(request)
```

## 📊 Performance Impact

### Overhead
- **Memory**: ~1KB per active rate limit key
- **CPU**: <1ms per request for rate limit check
- **Network**: Minimal (Redis operations are <1ms)

### Scalability
- **Horizontal**: Redis clustering supports unlimited scale
- **Vertical**: Single Redis instance handles 100K+ requests/second
- **Failover**: Graceful degradation to in-memory on Redis failure

## ✅ Deployment Checklist

Before deploying to production:

- [ ] Redis configured and accessible
- [ ] `BYPASS_RATE_LIMITING=false` in production
- [ ] Rate limit tests passing
- [ ] Monitoring and alerting configured
- [ ] Documentation updated for team
- [ ] Rate limits reviewed and approved by security team

## 🆘 Emergency Procedures

### Disable Rate Limiting (Emergency Only)
```bash
# Temporary bypass for critical issues
railway variables set BYPASS_RATE_LIMITING=true
railway deploy

# Remember to re-enable after resolution
railway variables set BYPASS_RATE_LIMITING=false
railway deploy
```

### Adjust Limits During High Traffic
```python
# In rate_limiting.py, temporarily increase limits
RATE_LIMITS = {
    "analysis_create": "10/minute",  # Increased from 3/minute
    "api_general": "2000/minute",    # Increased from 1000/minute
    # ... other limits
}
```

---

## 📞 Support

For rate limiting issues:
1. Check this guide first
2. Review application logs
3. Test with rate limiting disabled locally
4. Contact DevOps team for Redis issues
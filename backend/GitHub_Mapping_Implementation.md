# GitHub Auto-Mapping Implementation

## Overview
This document outlines the implementation of GitHub auto-mapping functionality that matches Rootly users to their GitHub accounts using name-based fuzzy matching.

## Problem Statement
- GitHub users typically have private email addresses (`"email": null` in API responses)
- Email-based matching was failing with "Skipping user Unknown - no email address" errors
- Need to match Rootly user names like "Spencer Cheng" to GitHub usernames like "spencerhcheng"

## Solution Architecture

### Core Components
1. **EnhancedGitHubMatcher** (`/backend/app/services/enhanced_github_matcher.py`)
2. **Auto-mapping Endpoint** (`/backend/app/api/endpoints/manual_mappings.py`)
3. **Frontend Integration** (`mapping-drawer.tsx`)

### Matching Strategy
```
1. Organization Discovery → Discover orgs from GitHub token using /user/orgs API
2. Member Bulk Fetch → Get all members + profiles from discovered organizations  
3. Fuzzy Name Matching → Match Rootly names against GitHub profile names
4. Pattern Matching → Try username patterns (spencer.cheng → spencercheng)
5. Candidate Selection → Choose best match with confidence scoring
```

## Implementation Details

### 1. Organization Discovery
- **Method**: `discover_accessible_organizations()`
- **API Calls**: `/user/orgs`, `/users/{username}/orgs`
- **Fallback**: `["Rootly-AI-Labs", "rootlyhq"]`

```python
orgs_url = "https://api.github.com/user/orgs"
org_names = [org['login'] for org in orgs_data]
```

### 2. Member Fetching  
- **Global Cache**: `_GLOBAL_ORG_CACHE` persists across instances
- **Rate Limiting**: 1 second pause every 5 API calls
- **Error Handling**: Continue processing if individual users fail

```python
# Get org members list  
members = await self._get_org_members(org, session)
# Get profiles for each member
profile = await self._get_github_user_profile(username, session)
```

### 3. Fuzzy Name Matching
- **Multi-strategy scoring** with weighted combinations:
  - Direct string similarity (30%)
  - Component presence (40% - both first/last names found)
  - Word-based similarity (20% - handles reordering)
  - Initial matching (10% - "Spencer C." recognition)

```python
final_score = (
    direct_sim * 0.3 +           # "spencer cheng" vs "spencer c"
    component_score * 0.4 +      # both "spencer" and "cheng" found
    word_similarity * 0.2 +      # word intersection/union  
    initial_score * 0.1          # abbreviated names bonus
)
```

### 4. Confidence Thresholds
- **95%+ similarity**: Immediate match (high confidence)
- **70-95%**: Candidate for consideration  
- **80%+ for ambiguous cases**: Higher threshold when multiple candidates
- **Clear winner**: Must be 10% better than second-best candidate

## Key Findings & Challenges

### Issues Discovered
1. **Hardcoded Organizations**: Initially used `["rootly-hq"]` instead of discovering from token
2. **Email Privacy**: All GitHub emails returned `null` due to privacy settings  
3. **Regex Errors**: `[^\w\s-.]` caused `bad character range \s-.` errors
4. **Connection Resets**: Too many concurrent API calls caused `ERR_CONNECTION_RESET`
5. **HTTP2 Protocol Errors**: Server timeouts due to long-running requests
6. **Cache Persistence**: Instance-level caches didn't persist across requests

### Solutions Implemented
1. **Dynamic Org Discovery**: Use GitHub token to discover accessible organizations
2. **Name-First Approach**: Skip email verification entirely, focus on names  
3. **Proper Regex**: Use `[^\w\s\-\.]` with escaped characters
4. **Rate Limiting**: Pause every 5 requests to prevent API overload
5. **Request Timeouts**: 45-second limit, process max 20 users per request
6. **Global Caching**: Persist org/member data across matcher instances

## Performance Characteristics

### Timing Expectations
- **First Run**: 15-40 seconds (fetch + cache members)
- **Subsequent Runs**: 5-15 seconds (use cached data)
- **Per User**: ~1-3 seconds matching against cached members

### API Usage
- **Organization Discovery**: 1-2 calls
- **Member Fetching**: 1 call per org + 1 call per member profile
- **Matching Phase**: 0 calls (uses cached data)

### Rate Limiting
```python
if member_count > 0 and member_count % 5 == 0:
    await asyncio.sleep(1)  # Pause every 5 requests
```

## Code Examples

### Successful Match Logs
```
🔄 Fetching members from organization: rootlyhq
📥 Cached 25 usernames for rootlyhq
✅ Loaded 22 profiles from rootlyhq (25 total members)
🎯 Matching 'Spencer Cheng' against 22 org members with profiles
🎯 HIGH SIMILARITY match: 'Spencer Cheng' ~= 'spencer cheng' (score: 0.98) -> spencerhcheng
✅ Found match: 'Spencer Cheng' -> spencerhcheng
```

### Multiple Candidates
```
🤔 Multiple candidates for 'John Smith':
   - john-smith: 'john smith' (score: 0.95)
   - johnsmith123: 'john s' (score: 0.82)  
   - js-dev: 'john smith' (score: 0.87)
🎯 BEST CANDIDATE match: 'John Smith' ~= 'john smith' (score: 0.95) -> john-smith
```

## Current Limitations

### 1. User Limit
- **Constraint**: 20 users per request to prevent timeouts
- **Workaround**: Users need multiple runs for large teams
- **Future**: Implement pagination or background processing

### 2. Organization Scope
- **Constraint**: Only matches users within discovered GitHub organizations  
- **Impact**: External contributors won't be matched
- **Mitigation**: Ensure all team members are in GitHub orgs

### 3. Name Variations
- **Challenge**: Nicknames, cultural names, special characters
- **Examples**: "Alex" vs "Alexander", "José" vs "Jose"  
- **Mitigation**: Fuzzy matching helps but not perfect

## Future Improvements

### 1. Background Processing
```python
# Instead of synchronous processing
@router.post("/manual-mappings/run-github-mapping-async")
async def run_github_mapping_async():
    # Queue background task
    # Return job_id for status polling
```

### 2. Enhanced Fuzzy Matching  
- **Phonetic matching** for similar-sounding names
- **Cultural name variants** (Alex/Alexander, Rob/Robert)  
- **Special character normalization** (José → Jose)

### 3. Manual Override System
```python
# For ambiguous cases, present candidates to user
{
    "candidates": [
        {"username": "john-smith", "confidence": 0.95, "github_name": "John Smith"},
        {"username": "johnsmith123", "confidence": 0.87, "github_name": "J Smith"}
    ],
    "requires_manual_selection": true
}
```

### 4. Caching Improvements
- **Redis cache** for production scalability
- **TTL expiration** for org member data
- **Smart invalidation** when org membership changes

## Testing Recommendations

### 1. Name Variation Tests
```python
test_cases = [
    ("Spencer Cheng", "spencer cheng", 0.98),  # Case difference
    ("Spencer Cheng", "Spencer C.", 0.85),     # Abbreviated  
    ("John Smith Jr", "John Smith", 0.90),     # Suffix removal
    ("José García", "Jose Garcia", 0.95),      # Accent normalization
]
```

### 2. Edge Cases
- Empty GitHub organization
- All private GitHub profiles
- Network timeouts/failures
- Rate limit exceeded scenarios

### 3. Performance Testing
- Large organizations (100+ members)
- Concurrent mapping requests  
- Memory usage during bulk operations

## Deployment Notes

### Environment Variables
```bash
# GitHub token should have these scopes:
# - read:user (user profile access)
# - read:org (organization membership)
# - repo (if private repo access needed)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

### Railway Configuration
- **Timeout**: Ensure Railway allows 60+ second requests
- **Memory**: Monitor usage during bulk member fetching
- **Logging**: Set appropriate log levels for debugging

## Troubleshooting Guide

### Common Errors

#### "No organization members found to match against"
- **Cause**: Organization cache failed to populate
- **Check**: GitHub token permissions and org access
- **Fix**: Verify token has `read:org` scope

#### "ERR_HTTP2_PROTOCOL_ERROR" 
- **Cause**: Request timeout on server side
- **Check**: Request duration, user count  
- **Fix**: Reduce batch size, add timeouts

#### "bad character range \s-. at position 4"
- **Cause**: Invalid regex character range
- **Status**: Fixed in current implementation
- **Pattern**: Use `[^\w\s\-\.]` instead of `[^\w\s-.]`

### Debug Commands
```python
# Check org cache status
logger.info(f"Cache: {[(org, len(members)) for org, members in self._org_members_cache.items()]}")

# Test name similarity  
similarity = self._calculate_name_similarity("Spencer Cheng", "spencer c", "spencer", "cheng")
logger.info(f"Similarity: {similarity}")
```

## Success Metrics

### Expected Results
- **Match Rate**: 70-90% for active GitHub users in organizations
- **False Positives**: <5% (wrong person matched)
- **Processing Time**: <60 seconds for 20 users
- **API Efficiency**: <100 GitHub API calls per 20 users

### Monitoring
```python
# Track in logs/metrics
{
    "total_processed": 20,
    "mapped": 15,  # 75% success rate
    "not_found": 4,
    "errors": 1,
    "processing_time": 23.5,  # seconds
    "api_calls_used": 67
}
```

---

**Last Updated**: 2025-08-27  
**Implementation Status**: ✅ Production Ready
**Key Contributors**: Claude Code, Spencer Cheng
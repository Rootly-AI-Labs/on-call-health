# Phase 2: Validation Infrastructure - Research

**Researched:** 2026-02-01
**Domain:** Token validation system with type-aware handling, caching, and UI status indicators
**Confidence:** HIGH

## Summary

Research into the On-Call-Health codebase reveals that **substantial validation infrastructure already exists** and Phase 2 is primarily about extending, not rebuilding. The `IntegrationValidator` service already validates tokens for GitHub, Linear, and Jira integrations, with caching (5-minute TTL in Redis with in-memory fallback), error categorization, and token refresh coordination. The frontend already has `token_valid` and `token_error` fields displayed in connected cards.

The primary work for this phase is:
1. **Add type-aware validation** - Extend validation to distinguish OAuth (refresh-capable) from manual tokens (no refresh, needs different error handling)
2. **Validate during setup** - Add pre-save validation endpoint that validates immediately when user enters token
3. **Enhance error messages** - Make error messages platform-specific with actionable guidance (links to docs, required permissions)
4. **Add visual status indicators** - Implement real-time status updates during validation (validating, connected, error, disconnected states)
5. **Extend notification system** - Create notifications for post-setup validation failures

**Primary recommendation:** Extend the existing `IntegrationValidator` service to support manual token validation, add a new validation endpoint for setup flow, and enhance the frontend cards with real-time status indicators using polling.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| IntegrationValidator | existing | Token validation service | Already implements OAuth validation patterns |
| validation_cache.py | existing | Redis/memory caching | 5-min TTL cache for validation results |
| httpx | existing | Async HTTP client | Used for all external API validation calls |
| NotificationService | existing | User notifications | Existing notification infrastructure to extend |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cryptography (Fernet) | existing | Token encryption | Decrypting tokens before validation |
| redis | existing | Distributed caching | Validation result caching |
| zod (frontend) | existing | Form validation | Token format validation on frontend |
| shadcn/ui | existing | UI components | Status badges, alerts, toast notifications |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Polling for status | WebSocket | WebSocket adds complexity; polling every 5min already exists for notifications |
| Redis caching | In-memory only | Redis already configured, provides persistence across restarts |

**Installation:**
No new packages required - all dependencies already in project.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/services/
├── integration_validator.py     # EXTEND - add manual token validation
├── token_manager.py            # EXISTS - Phase 1 token retrieval
├── notification_service.py      # EXTEND - add token failure notifications
└── validation_cache.py         # EXISTS - reuse for 15-min cache

backend/app/api/endpoints/
├── jira.py                     # EXTEND - add validate-token endpoint
└── linear.py                   # EXTEND - add validate-token endpoint

frontend/src/app/integrations/
├── components/
│   ├── JiraConnectedCard.tsx   # EXTEND - real-time status
│   └── LinearConnectedCard.tsx # EXTEND - real-time status
└── hooks/
    └── useValidation.ts        # NEW - validation status hook
```

### Pattern 1: Pre-Save Validation Flow
**What:** Validate token immediately after user enters it, before clicking save
**When to use:** Initial integration setup
**Example:**
```python
# Source: Pattern derived from existing IntegrationValidator
@router.post("/validate-token")
async def validate_token(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate token before saving to database."""
    body = await request.json()
    token = body.get("token")

    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    # Validate format first (fast fail)
    if not is_valid_token_format(token):
        return {
            "valid": False,
            "error": "Invalid token format",
            "error_type": "format"
        }

    # Validate against API
    validator = IntegrationValidator(db)
    result = await validator.validate_manual_token(
        provider="jira",  # or "linear"
        token=token,
        site_url=body.get("site_url")  # Jira-specific
    )

    return {
        "valid": result["valid"],
        "error": result.get("error"),
        "error_type": result.get("error_type"),
        "user_info": result.get("user_info")  # Display name, email
    }
```

### Pattern 2: Type-Aware Validation in IntegrationValidator
**What:** Different validation paths for OAuth vs manual tokens
**When to use:** All token validation calls
**Example:**
```python
# Source: Pattern derived from existing _validate_jira, _validate_linear methods
async def _validate_with_type_awareness(
    self,
    integration: Union[JiraIntegration, LinearIntegration]
) -> Dict[str, Any]:
    """Validate token with type-aware error handling."""

    if integration.is_oauth:
        # OAuth path: try refresh if expired
        try:
            token = await self._get_valid_token_with_refresh(integration)
        except ValueError as e:
            return self._error_response(str(e), error_type="authentication")
    else:
        # Manual path: no refresh, validate directly
        if not integration.has_token:
            return self._error_response(
                "No API token configured",
                error_type="missing"
            )
        token = decrypt_token(integration.access_token)

    # Make validation API call with decrypted token
    result = await self._call_validation_api(integration, token)
    return result

def _error_response(
    self,
    error_msg: str,
    error_type: str = "unknown"
) -> Dict[str, Any]:
    """Create error response with type for frontend handling."""
    return {
        "valid": False,
        "error": error_msg,
        "error_type": error_type  # authentication, permissions, network, format
    }
```

### Pattern 3: Real-Time Status Indicator (Frontend)
**What:** Visual status that updates during validation
**When to use:** Integration cards and setup modal
**Example:**
```typescript
// Source: Pattern derived from existing JiraConnectedCard.tsx
type ConnectionStatus = 'connected' | 'validating' | 'error' | 'disconnected';

interface StatusIndicatorProps {
  status: ConnectionStatus;
  authMethod: 'oauth' | 'manual';
  error?: string | null;
}

function StatusIndicator({ status, authMethod, error }: StatusIndicatorProps) {
  const statusConfig = {
    connected: {
      badge: "bg-green-100 text-green-700",
      icon: CheckCircle,
      text: `Connected via ${authMethod === 'oauth' ? 'OAuth' : 'API Token'}`
    },
    validating: {
      badge: "bg-blue-100 text-blue-700",
      icon: Loader2,
      text: "Validating..."
    },
    error: {
      badge: "bg-red-100 text-red-700",
      icon: AlertTriangle,
      text: "Connection Error"
    },
    disconnected: {
      badge: "bg-gray-100 text-gray-600",
      icon: XCircle,
      text: "Not Connected"
    }
  };

  const config = statusConfig[status];

  return (
    <Badge className={config.badge}>
      <config.icon className={`w-3 h-3 mr-1 ${status === 'validating' ? 'animate-spin' : ''}`} />
      {config.text}
    </Badge>
  );
}
```

### Pattern 4: Platform-Specific Error Messages
**What:** Error messages that reference platform concepts and provide actionable guidance
**When to use:** All validation error responses
**Example:**
```python
# Source: Pattern derived from existing error handling, enhanced per CONTEXT.md
JIRA_ERROR_MESSAGES = {
    "authentication": {
        "message": "Invalid Jira Personal Access Token. The token may be expired or incorrectly entered.",
        "help_url": "https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/",
        "action": "Generate a new token in Atlassian Account Settings > Security > API Tokens"
    },
    "permissions": {
        "message": "Your Jira token lacks required permissions to access issue data.",
        "help_url": "https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/",
        "action": "Ensure your Atlassian account has read access to the projects you want to analyze"
    },
    "network": {
        "message": "Cannot reach Jira API. Check your network connection.",
        "action": "Verify you can access your Jira site in a browser"
    },
    "format": {
        "message": "Invalid token format. Jira API tokens should be alphanumeric.",
        "action": "Copy the token exactly as shown in Atlassian Account Settings"
    }
}

LINEAR_ERROR_MESSAGES = {
    "authentication": {
        "message": "Invalid Linear Personal API Key. The key may be expired or incorrectly entered.",
        "help_url": "https://linear.app/settings/account/api",
        "action": "Generate a new API key in Linear Settings > Account > API > Personal API Keys"
    },
    "permissions": {
        "message": "Your Linear API key lacks required scopes. Ensure 'read' scope is enabled.",
        "help_url": "https://developers.linear.app/docs/graphql/working-with-the-graphql-api",
        "action": "Create a new API key with at least 'read:issue' and 'read:user' scopes"
    },
    # ... similar for network, format
}
```

### Anti-Patterns to Avoid
- **Don't validate in the save handler:** Validation should complete BEFORE save is clicked (per CONTEXT.md)
- **Don't skip format validation:** Check token format before making API calls (fast fail)
- **Don't use generic error messages:** Each failure type needs platform-specific actionable guidance
- **Don't cache failed validations indefinitely:** Errors should be re-checked on next request

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token decryption | Custom decryption | `decrypt_token()` in integration_validator.py | Already handles key derivation, Fernet setup |
| Validation caching | In-memory dict | `validation_cache.py` | Handles Redis, TTL, in-memory fallback |
| HTTP errors | Custom error classes | httpx exceptions | TimeoutException, NetworkError already categorized |
| Toast notifications | Custom toast | shadcn/ui toast + useToast hook | Already styled, accessible, in use |
| Status badges | Custom styling | shadcn/ui Badge | Consistent with existing UI |
| Notification creation | Direct DB inserts | NotificationService | Handles user lookup, org admins, priority |

**Key insight:** The codebase already has well-structured validation, caching, and notification infrastructure. Phase 2 extends these patterns rather than creating new ones.

## Common Pitfalls

### Pitfall 1: Validating After Save
**What goes wrong:** User clicks save, validation fails, but token is already stored with invalid state
**Why it happens:** Natural to validate in the save handler
**How to avoid:** Validate on token entry (debounced), show spinner on save button if validation in progress
**Warning signs:** `token_valid: false` immediately after setup completes

### Pitfall 2: Generic Error Messages
**What goes wrong:** User sees "Token invalid" with no guidance on how to fix
**Why it happens:** Reusing OAuth error messages for manual tokens
**How to avoid:** Use platform-specific error message maps (JIRA_ERROR_MESSAGES, LINEAR_ERROR_MESSAGES)
**Warning signs:** User repeatedly enters same invalid token

### Pitfall 3: Blocking UI During Validation
**What goes wrong:** UI freezes while waiting for validation API call
**Why it happens:** Not showing loading state during validation
**How to avoid:** Show "Validating..." state immediately, update to success/error when complete
**Warning signs:** User clicks save multiple times thinking nothing happened

### Pitfall 4: Leaking Tokens in Error Messages
**What goes wrong:** Token appears in error message or logs
**Why it happens:** Including token in ValueError or log statements
**How to avoid:** Never include actual token values in error messages; use "token" or "***" placeholder
**Warning signs:** Security tests failing, tokens visible in browser console

### Pitfall 5: Not Clearing Stale Status
**What goes wrong:** "Connected" status shows even after token is invalidated
**Why it happens:** Cache not invalidated when user updates token
**How to avoid:** Call `invalidate_validation_cache(user_id)` when token changes
**Warning signs:** User sees "Connected" but operations fail

### Pitfall 6: Different UX for OAuth vs Manual
**What goes wrong:** OAuth users see one experience, manual token users see different
**Why it happens:** Implementing manual flow separately from OAuth flow
**How to avoid:** Same status indicators, same error display for both; only error message content differs
**Warning signs:** Inconsistent UI between integration types

## Code Examples

Verified patterns from the codebase:

### Existing Validation Call Pattern
```python
# Source: backend/app/api/endpoints/jira.py lines 341-347, linear.py lines 378-384
# Validate token
from app.services.integration_validator import IntegrationValidator
validator = IntegrationValidator(db)
validation_result = await validator._validate_jira(current_user.id)

token_valid = validation_result.get("valid", False) if validation_result else False
token_error = validation_result.get("error") if validation_result and not token_valid else None
```

### Existing Cache Invalidation Pattern
```python
# Source: backend/app/api/endpoints/jira.py lines 1035-1036
from ...services.integration_validator import invalidate_validation_cache
invalidate_validation_cache(current_user.id)
```

### Existing Error Response Pattern
```python
# Source: backend/app/services/integration_validator.py lines 666-687
def _error_response(self, error_msg: str) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {"valid": False, "error": error_msg}

def _handle_api_response(self, response, user_id: int, provider: str) -> Dict[str, Any]:
    """Handle REST API responses with standard status codes."""
    if response.status_code == 200:
        return {"valid": True, "error": None}
    elif response.status_code == 401:
        return self._error_response(
            f"{provider} token is expired or invalid. Please reconnect your {provider} integration."
        )
    elif response.status_code == 403:
        return self._error_response(
            f"{provider} token lacks required permissions. Please reconnect with proper scopes."
        )
```

### Existing Frontend Status Display
```typescript
// Source: frontend/src/app/integrations/components/JiraConnectedCard.tsx lines 27-51
const hasTokenError = integration.token_valid === false

return (
  <Card className={`border-2 ${hasTokenError ? 'border-red-200 bg-red-50/50' : 'border-green-200 bg-green-50/50'}`}>
    {/* ... */}
    {hasTokenError ? (
      <Badge variant="secondary" className="bg-red-100 text-red-700">
        <AlertTriangle className="w-3 h-3 mr-1" />
        Token Invalid
      </Badge>
    ) : (
      <Badge variant="secondary" className="bg-green-100 text-green-700">
        <CheckCircle className="w-3 h-3 mr-1" />
        Connected
      </Badge>
    )}
```

### Existing Notification Creation Pattern
```python
# Source: backend/app/services/notification_service.py lines 150-186
def create_slack_connected_notification(self, connected_by: User, workspace_name: str) -> List[UserNotification]:
    """Notify all org members when Slack workspace is connected."""
    notifications = []

    if not connected_by.organization_id:
        return notifications

    org_members = self.db.query(User).filter(
        User.organization_id == connected_by.organization_id,
        User.status == 'active'
    ).all()

    for member in org_members:
        notification = UserNotification(
            user_id=member.id,
            organization_id=connected_by.organization_id,
            type='integration',
            title=title,
            message=message,
            priority='normal'
        )
        notifications.append(notification)
        self.db.add(notification)

    self.db.commit()
    return notifications
```

### Existing Polling Pattern (Frontend)
```typescript
// Source: frontend/src/hooks/useNotifications.ts lines 205-223
useEffect(() => {
  fetchNotifications()

  const interval = setInterval(fetchNotifications, POLLING_INTERVAL_MS)

  function handleVisibilityChange(): void {
    if (document.visibilityState === 'visible') {
      fetchNotifications()
    }
  }
  document.addEventListener('visibilitychange', handleVisibilityChange)

  return () => {
    clearInterval(interval)
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    abortControllerRef.current?.abort()
  }
}, [])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Validate only on /status call | Validate during setup (Phase 2) | This phase | Catch invalid tokens before saving |
| Generic error messages | Platform-specific messages (Phase 2) | This phase | Better user guidance |
| OAuth-only validation | OAuth + Manual token validation (Phase 2) | This phase | Support for API tokens |

**Already implemented:**
- Token validation via `IntegrationValidator` service
- Caching with 5-minute TTL via `validation_cache.py`
- Frontend `token_valid` and `token_error` display
- OAuth token refresh with distributed locking
- Notification system for integration events

**To be implemented (Phase 2):**
- Pre-save validation endpoint
- Manual token validation path in IntegrationValidator
- Platform-specific error message maps
- Enhanced status indicators with "validating" state
- Token validation failure notifications

## Implementation Checklist (Verified Against CONTEXT.md)

Based on user decisions, the following must be implemented:

### 1. Backend: Validation Endpoint (NEW)
- [ ] Add `POST /api/jira/validate-token` endpoint
- [ ] Add `POST /api/linear/validate-token` endpoint
- [ ] Return validation result with `error_type` for frontend handling
- [ ] Include user info (display_name, email) on success

### 2. Backend: Type-Aware Validation (EXTEND IntegrationValidator)
- [ ] Add `validate_manual_token()` method for Jira
- [ ] Add `validate_manual_token()` method for Linear
- [ ] Distinguish OAuth vs manual in error handling
- [ ] Update cache TTL to 15 minutes (per CONTEXT.md)

### 3. Backend: Error Messages (NEW)
- [ ] Create `JIRA_ERROR_MESSAGES` dictionary with platform-specific messages
- [ ] Create `LINEAR_ERROR_MESSAGES` dictionary with platform-specific messages
- [ ] Include help URLs and actionable next steps
- [ ] Test that error messages don't leak tokens

### 4. Backend: Notifications (EXTEND NotificationService)
- [ ] Add `create_token_validation_failure_notification()` method
- [ ] Notify user when post-setup validation fails
- [ ] Include error type and guidance in notification

### 5. Frontend: Status Indicators (EXTEND Connected Cards)
- [ ] Add "validating" state with spinner
- [ ] Show "Connected via OAuth" or "Connected via API Token"
- [ ] Update status without page refresh (polling on /status)
- [ ] Apply same patterns to all integration cards (GitHub, Jira, Linear)

### 6. Frontend: Setup Flow (NEW/EXTEND)
- [ ] Add token input with immediate validation (debounced)
- [ ] Show validation status as user types
- [ ] Disable save button until validation passes
- [ ] Show spinner on save if validation in progress

## Open Questions

Things resolved during research:

1. **Real-time updates: WebSocket vs Polling?**
   - Resolved: Use polling (already in place for notifications, 5-min interval)
   - Justification: WebSocket adds complexity, polling is "good enough" for status

2. **Cache TTL: 5 minutes vs 15 minutes?**
   - CONTEXT.md says 15-minute cache for periodic validation
   - Current implementation uses 5-minute TTL
   - Recommendation: Update to 15 minutes as specified in CONTEXT.md

3. **Where to store error messages?**
   - Recommendation: Create new file `backend/app/core/error_messages.py` for platform-specific error maps
   - This keeps messages centralized and easily editable

## Sources

### Primary (HIGH confidence)
- `backend/app/services/integration_validator.py` - Existing validation service (lines 138-716)
- `backend/app/core/validation_cache.py` - Caching implementation (full file)
- `backend/app/api/endpoints/jira.py` - Status endpoint pattern (lines 323-391)
- `backend/app/api/endpoints/linear.py` - Status endpoint pattern (lines 357-428)
- `frontend/src/app/integrations/components/JiraConnectedCard.tsx` - Status display (full file)
- `frontend/src/app/integrations/components/LinearConnectedCard.tsx` - Status display (full file)
- `backend/app/services/notification_service.py` - Notification patterns (full file)
- `frontend/src/hooks/useNotifications.ts` - Polling pattern (lines 205-223)

### Secondary (MEDIUM confidence)
- `.planning/phases/02-validation-infrastructure/02-CONTEXT.md` - User decisions
- `.planning/phases/01-backend-foundation/01-RESEARCH.md` - Phase 1 patterns

### Tertiary (LOW confidence)
- None - all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries/services already in use
- Architecture: HIGH - Patterns extracted from existing codebase
- Error messages: MEDIUM - Platform-specific messages need content review
- Pitfalls: HIGH - Based on actual codebase patterns and CONTEXT.md decisions

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (30 days - stable patterns, no external dependencies)

---

## Key Insight for Planner

**Phase 2 is primarily about extending existing infrastructure, not building new systems.**

The validation service, caching, notification system, and frontend components already exist and work well. The work is:
1. Adding a new validation endpoint for pre-save validation
2. Extending IntegrationValidator with manual token validation methods
3. Creating platform-specific error message maps
4. Enhancing frontend status indicators with "validating" state

**Recommended task breakdown:**
1. Backend: Add validate-token endpoint (Jira)
2. Backend: Add validate-token endpoint (Linear)
3. Backend: Extend IntegrationValidator for manual tokens
4. Backend: Create error message maps with platform-specific content
5. Backend: Add token validation failure notifications
6. Frontend: Add validation status hook
7. Frontend: Enhance connected cards with real-time status
8. Frontend: Update setup flow with pre-save validation
9. Tests: Validation endpoint tests
10. Tests: Error message tests (no token leakage)

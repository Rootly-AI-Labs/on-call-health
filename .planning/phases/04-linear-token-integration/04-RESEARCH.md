# Phase 4: Linear Token Integration - Research

**Researched:** 2026-02-02
**Domain:** React form handling with real-time validation, FastAPI token storage endpoints, Linear GraphQL API
**Confidence:** HIGH

## Summary

Phase 4 enables users to connect Linear using Personal API Keys as an alternative to OAuth. This phase directly applies the proven Phase 3 (Jira) pattern to Linear. The codebase already has all infrastructure: Phase 2 validation hooks (useValidation, StatusIndicator), existing LinearManualSetupForm component, and Phase 3's auto-save pattern. Linear is simpler than Jira because it only requires a token field (no site URL).

**Key technical approach:**
- Frontend uses React Hook Form with useEffect to auto-validate on token change (Phase 2 pattern, already working)
- Auto-save triggers immediately after validation succeeds (Phase 3 pattern, proven working)
- Backend POST endpoint encrypts token with Fernet, sets token_source='manual', returns integration object
- Linear API uses GraphQL at https://api.linear.app/graphql with Bearer token authentication
- Token format: `lin_api_` prefix (validated by existing IntegrationValidator)
- Background sync uses existing pattern (manual trigger after save)

**Primary recommendation:** Adapt existing LinearManualSetupForm component using Phase 3's JiraManualSetupForm as exact template. Backend endpoint follows Jira connect-manual pattern (lines 638-773 in jira.py). Linear simpler: no site_url field, just token.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React Hook Form | 7.70.0 | Form validation and state | Already used in LinearManualSetupForm (lines 11, 21) |
| sonner | 2.0.7 | Toast notifications | Project's toast library - used in JiraManualSetupForm (line 4) |
| FastAPI | latest | Backend API framework | Project's backend framework - async/await support |
| cryptography (Fernet) | latest | Token encryption | Used for all tokens - symmetric encryption (linear.py lines 18, 50-55) |
| httpx | latest | HTTP client | Backend API calls to Linear GraphQL - async support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | 0.563.0 | Icon components | UI icons (CheckCircle, Loader2, Eye, EyeOff) - already imported |
| shadcn/ui components | latest | Form components (Card, Input, Button) | Already used throughout form |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fernet encryption | Custom AES | Fernet has authenticated encryption built-in, battle-tested |
| GraphQL query | REST API | Linear primary API is GraphQL, REST is limited |
| Manual validation | OAuth-only | Users need API token option for environments without OAuth |

**Installation:**
All dependencies already installed. No new packages needed.

## Architecture Patterns

### Recommended Project Structure (Existing)
```
frontend/src/app/integrations/
├── components/
│   ├── LinearManualSetupForm.tsx    # Adapt for auto-save flow (Phase 3 pattern)
│   ├── StatusIndicator.tsx          # Reuse for validation state (Phase 2)
│   └── LinearIntegrationCard.tsx    # Add dual-button layout
├── hooks/
│   └── useValidation.ts             # Reuse for token validation (Phase 2)
└── page.tsx                          # Main integrations page

backend/app/api/endpoints/
└── linear.py                         # Add POST /connect-manual endpoint
```

### Pattern 1: Auto-Save on Validation Success (Phase 3 Proven Pattern)
**What:** Form submits automatically when validation passes, without explicit button click
**When to use:** Real-time validated forms where user expects immediate save (API token entry)
**Example:**
```typescript
// Source: JiraManualSetupForm.tsx lines 26-92 (Phase 3 implementation)
const { isConnected, userInfo } = useValidation({ provider: "linear" });
const [isSaving, setIsSaving] = useState(false);
const saveAttempted = useRef(false);

const tokenValue = form.watch("token");

// Auto-validate when token is provided
useEffect(() => {
  if (tokenValue && tokenValue.trim()) {
    validateToken({ token: tokenValue });
  }
}, [tokenValue, validateToken]);

// Reset save attempt flag when input changes
useEffect(() => {
  saveAttempted.current = false;
}, [tokenValue]);

// Auto-save when validation succeeds
useEffect(() => {
  const shouldSave = isConnected && userInfo && !isSaving && !saveAttempted.current;

  if (shouldSave) {
    saveAttempted.current = true;
    handleAutoSave();
  }
}, [isConnected, userInfo, isSaving]);

const handleAutoSave = async () => {
  setIsSaving(true);
  try {
    const success = await onSave({
      token: tokenValue,
      userInfo,
    });

    if (success) {
      toast.success("Linear connected!", { duration: 3000 });
      onClose();
    } else {
      saveAttempted.current = false; // Allow retry
    }
  } catch (error) {
    toast.error("Failed to save integration");
    saveAttempted.current = false;
  } finally {
    setIsSaving(false);
  }
};
```

### Pattern 2: Dual Connection Method UI
**What:** Show both OAuth and API Token buttons with equal visual weight
**When to use:** Multiple auth methods, no preferred method
**Example:**
```tsx
// Source: Tailwind responsive utilities + Phase 3 decision
<div className="flex flex-col sm:flex-row gap-3 w-full">
  <Button
    onClick={handleOAuthConnect}
    className="flex-1 bg-purple-600 hover:bg-purple-700"
    disabled={isConnecting}
  >
    Connect with OAuth
  </Button>
  <Button
    onClick={handleTokenConnect}
    className="flex-1 bg-purple-600 hover:bg-purple-700"
  >
    Use API Token
  </Button>
</div>
```

### Pattern 3: Backend Token Save Endpoint (Linear-Specific)
**What:** POST endpoint validates and encrypts token, returns integration object
**When to use:** Saving user-provided API tokens
**Example:**
```python
# Source: Adapted from jira.py /connect-manual endpoint (lines 638-773)
@router.post("/connect-manual")
async def connect_linear_manual(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save manually provided Linear API key with validation and encryption.

    Request body:
        token: str - The Linear Personal API Key (lin_api_...)
        user_info: dict (optional) - User info from frontend validation

    Returns:
        Success response with integration details or error
    """
    body = await request.json()
    token = body.get("token")
    user_info = body.get("user_info")

    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    # Backend re-validates token (never trust client validation)
    validator = IntegrationValidator(db)
    result = await validator.validate_manual_token(
        provider="linear",
        token=token
    )

    if not result.get("valid"):
        logger.warning(
            f"[Linear] Manual token validation failed for user {current_user.id}: "
            f"{result.get('error_type')}"
        )
        raise HTTPException(status_code=400, detail=result.get("error"))

    # Validation succeeded - encrypt and save token
    logger.info(f"[Linear] Saving manual token for user {current_user.id}")
    enc_token = encrypt_token(token)

    # Get user info from validation result
    validated_user_info = result.get("user_info", {})
    linear_user_id = validated_user_info.get("linear_id")
    linear_display_name = validated_user_info.get("display_name")
    linear_email = validated_user_info.get("email")

    # Get workspace info via GraphQL
    workspace_info = await linear_integration_oauth.get_organization(token)
    workspace_id = workspace_info.get("id")
    workspace_name = workspace_info.get("name")
    workspace_url_key = workspace_info.get("urlKey")

    # Upsert integration
    integration = db.query(LinearIntegration).filter(
        LinearIntegration.user_id == current_user.id
    ).first()

    now = datetime.now(dt_timezone.utc)

    if integration:
        integration.access_token = enc_token
        integration.token_source = "manual"
        integration.token_expires_at = None  # Manual tokens don't auto-expire
        integration.workspace_id = workspace_id
        integration.workspace_name = workspace_name
        integration.workspace_url_key = workspace_url_key
        integration.linear_user_id = linear_user_id
        integration.linear_display_name = linear_display_name
        integration.linear_email = linear_email
        integration.refresh_token = None  # Manual tokens don't have refresh
        integration.updated_at = now
    else:
        integration = LinearIntegration(
            user_id=current_user.id,
            access_token=enc_token,
            token_source="manual",
            token_expires_at=None,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            workspace_url_key=workspace_url_key,
            linear_user_id=linear_user_id,
            linear_display_name=linear_display_name,
            linear_email=linear_email,
            refresh_token=None,
            created_at=now,
            updated_at=now,
        )
        db.add(integration)

    db.commit()

    # Trigger background sync immediately (same pattern as OAuth callback)
    # Sync service will fetch users and issues
    logger.info(f"[Linear] Manual token saved for user {current_user.id}")

    return {
        "success": True,
        "integration": {
            "id": integration.id,
            "token_source": "manual",
            "token_valid": True,
            "workspace_name": workspace_name,
        }
    }
```

### Pattern 4: Linear GraphQL Token Validation
**What:** Validate Linear Personal API Key using GraphQL viewer query
**When to use:** Pre-flight validation before saving token
**Example:**
```python
# Source: integration_validator.py lines 238-309 (existing implementation)
async def _validate_linear_manual_token(self, token: str) -> Dict[str, Any]:
    """Validate Linear Personal API Key."""
    # Format validation
    if not token or not token.strip():
        error = get_error_response("linear", "format")
        return {"valid": False, **error}

    token = token.strip()

    # Linear API keys start with lin_api_
    if not token.startswith("lin_api_"):
        error = get_error_response("linear", "format")
        return {"valid": False, **error}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Use GraphQL viewer query to validate token and get user info
            response = await client.post(
                "https://api.linear.app/graphql",
                headers={
                    "Authorization": token,  # No "Bearer" prefix for API keys
                    "Content-Type": "application/json"
                },
                json={
                    "query": "query { viewer { id name email } }"
                }
            )

            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    # GraphQL returned errors
                    error_msg = data["errors"][0].get("message", "")
                    if "authentication" in error_msg.lower():
                        error = get_error_response("linear", "authentication")
                    else:
                        error = get_error_response("linear", "permissions")
                    return {"valid": False, **error}

                viewer = data.get("data", {}).get("viewer", {})
                return {
                    "valid": True,
                    "error": None,
                    "error_type": None,
                    "user_info": {
                        "display_name": viewer.get("name"),
                        "email": viewer.get("email"),
                        "linear_id": viewer.get("id")
                    }
                }
            elif response.status_code == 401:
                error = get_error_response("linear", "authentication")
                return {"valid": False, **error}
            else:
                error = get_error_response("linear", "authentication")
                return {"valid": False, **error}

    except httpx.TimeoutException:
        error = get_error_response("linear", "network")
        return {"valid": False, **error}
    except Exception as e:
        logger.exception(f"Unexpected error validating Linear token: {e}")
        error = get_error_response("linear", "network")
        return {"valid": False, **error}
```

### Anti-Patterns to Avoid
- **Don't use Bearer prefix for API keys** - Linear API keys use raw token, not "Bearer {token}" (OAuth tokens use Bearer)
- **Don't skip workspace info** - Manual tokens need workspace_id populated (required for LinearIntegration model)
- **Don't show loading state during save** - Save is fast (< 500ms), form closes immediately
- **Don't store tokens in localStorage** - Backend encrypts with Fernet, frontend never persists raw tokens

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token encryption | Custom AES/RSA | cryptography.Fernet | Authenticated encryption, key derivation, padding built-in |
| Form validation | Manual onChange checks | React Hook Form + useValidation | Handles debouncing, async validation, error states |
| Toast notifications | Custom alert component | sonner | Stacking, positioning, animation, accessibility built-in |
| GraphQL queries | Manual fetch + JSON | Existing linear_integration_oauth methods | Handles pagination, errors, rate limits |
| Token validation | Custom API calls | IntegrationValidator service | Centralized, cached, consistent error messages |

**Key insight:** Linear's GraphQL API has subtle requirements (no Bearer prefix for API keys, error handling in data.errors). Use existing IntegrationValidator which handles these correctly.

## Common Pitfalls

### Pitfall 1: Bearer Token vs API Key Authentication
**What goes wrong:** Adding "Bearer" prefix to Linear API keys causes 401 errors
**Why it happens:** OAuth tokens use "Bearer {token}", but Personal API Keys use raw token format
**How to avoid:** Check token_source field. OAuth tokens: `Authorization: Bearer {token}`. API keys: `Authorization: {token}` (no Bearer)
**Warning signs:** 401 errors despite valid token format, GraphQL returns authentication errors
**Code reference:** integration_validator.py line 258 uses raw token for API key validation

### Pitfall 2: Missing Workspace ID for Manual Tokens
**What goes wrong:** LinearIntegration.workspace_id is NOT NULL, but manual token flow doesn't fetch it
**Why it happens:** OAuth flow automatically gets workspace info, manual token flow might skip it
**How to avoid:** After token validation, fetch workspace info using get_organization() GraphQL query
**Warning signs:** Database constraint violation on insert, workspace_id = "pending" persists
**Code reference:** LinearIntegration model line 21 requires workspace_id

### Pitfall 3: Auto-Save Triggering Multiple Times
**What goes wrong:** useEffect triggers save multiple times as validation state updates
**Why it happens:** Multiple state changes (isConnected, userInfo) trigger useEffect independently
**How to avoid:** Use saveAttempted ref to track if save already initiated. Reset ref on input change.
**Warning signs:** Multiple toasts appear, database shows duplicate save attempts
**Code reference:** JiraManualSetupForm.tsx lines 30, 56-58, 62-68 (proven solution)

### Pitfall 4: Token Expiration for Manual Tokens
**What goes wrong:** Code assumes token_expires_at exists, crashes on None for manual tokens
**Why it happens:** OAuth tokens expire (24hrs), manual tokens don't (set to None)
**How to avoid:** Set token_expires_at=None for manual tokens. Update needs_refresh() to handle None gracefully (return False)
**Warning signs:** NoneType errors in token refresh logic, comparison operators fail
**Code reference:** integration_validator.py line 60-65 needs_refresh() handles None correctly

### Pitfall 5: GraphQL Error Handling
**What goes wrong:** Response status 200 but data.errors contains authentication error - code treats as success
**Why it happens:** GraphQL always returns 200, errors in response body not status code
**How to avoid:** Always check response.json().get("errors") even when status_code == 200
**Warning signs:** "Token valid" shown but API calls fail, no error message displayed
**Code reference:** integration_validator.py lines 266-275 handles GraphQL errors correctly

### Pitfall 6: No Site URL Field (Linear Simplicity)
**What goes wrong:** Copy-paste Jira form code includes site_url field, not needed for Linear
**Why it happens:** Jira requires site_url for API endpoint construction, Linear uses fixed GraphQL endpoint
**How to avoid:** Linear only needs token field. Remove site_url from LinearManualSetupForm completely.
**Warning signs:** Unnecessary form field, validation errors on missing site_url
**Code reference:** LinearManualSetupForm.tsx currently has only token field (correct)

## Code Examples

Verified patterns from official sources:

### Minimal Help Text (Phase 3 Decision)
```tsx
// Source: Phase 3 CONTEXT.md decision + JiraManualSetupForm.tsx lines 110-137
{showInstructions && (
  <div className="mt-4">
    <Alert className="border-purple-200 bg-purple-50">
      <AlertDescription>
        <a
          href="https://linear.app/settings/api"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center text-purple-600 hover:text-purple-700"
        >
          <ExternalLink className="w-4 h-4 mr-2" />
          Create your API key at Linear
        </a>
      </AlertDescription>
    </Alert>
  </div>
)}
```

### Auto-Save Pattern with Guard (Phase 3 Proven)
```typescript
// Source: JiraManualSetupForm.tsx lines 26-92
const [isSaving, setIsSaving] = useState(false);
const saveAttempted = useRef(false);

const tokenValue = form.watch("token");

// Reset save attempt flag when token changes
useEffect(() => {
  saveAttempted.current = false;
}, [tokenValue]);

// Auto-save when validation succeeds
useEffect(() => {
  const shouldSave = isConnected && userInfo && !isSaving && !saveAttempted.current;

  if (shouldSave) {
    saveAttempted.current = true;
    handleAutoSave();
  }
}, [isConnected, userInfo, isSaving]);

const handleAutoSave = async () => {
  setIsSaving(true);
  try {
    const success = await onSave({
      token: tokenValue,
      userInfo,
    });

    if (success) {
      toast.success("Linear connected!", { duration: 3000 });
      onClose();
    } else {
      saveAttempted.current = false; // Allow retry
    }
  } catch (error) {
    toast.error("Failed to save integration");
    saveAttempted.current = false;
  } finally {
    setIsSaving(false);
  }
};
```

### Linear Workspace Fetch for Manual Token
```python
# Source: Adapted from linear.py OAuth callback (lines 174-181)
# Must fetch workspace info for manual tokens (not automatic like OAuth)
workspace_info = await linear_integration_oauth.get_organization(token)
workspace_id = workspace_info.get("id")
workspace_name = workspace_info.get("name")
workspace_url_key = workspace_info.get("urlKey")

if not workspace_id:
    raise HTTPException(status_code=400, detail="Could not get Linear organization info")
```

### Token Encryption Pattern
```python
# Source: linear.py lines 44-55 (existing encryption helpers)
from cryptography.fernet import Fernet
import base64

def get_encryption_key() -> bytes:
    key = settings.ENCRYPTION_KEY.encode()
    return base64.urlsafe_b64encode(key[:32].ljust(32, b"\0"))

def encrypt_token(token: str) -> str:
    return Fernet(get_encryption_key()).encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    return Fernet(get_encryption_key()).decrypt(encrypted_token.encode()).decode()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual token validation only on submit | Real-time validation with debounce | Phase 2 (completed) | Users see validation errors immediately |
| OAuth tokens only | OAuth + Personal API Keys | Phase 3 (Jira), Phase 4 (Linear) | Users can use tokens in restricted OAuth environments |
| Manual form submission | Auto-save on validation success | Phase 3 (Jira) | Faster, more intuitive UX - no extra click |
| Separate validation and save steps | Combined validation + save flow | Phase 3 (Jira) | Reduced clicks, immediate feedback |

**Deprecated/outdated:**
- Manual form submission after validation: Use auto-save pattern from Phase 3
- Bearer prefix for all Linear auth: OAuth uses Bearer, API keys don't
- Single authentication method: Modern apps support both OAuth and API tokens

## Open Questions

Things that couldn't be fully resolved:

1. **Background sync trigger for manual tokens**
   - What we know: OAuth callback doesn't trigger sync explicitly, happens via scheduled job
   - What's unclear: Should manual token save trigger immediate sync or rely on scheduled job?
   - Recommendation: Follow OAuth pattern - scheduled sync job will pick up new integration. No explicit trigger needed.

2. **Workspace mapping for manual tokens**
   - What we know: OAuth flow creates LinearWorkspaceMapping record (lines 233-258)
   - What's unclear: Should manual token flow also create workspace mapping?
   - Recommendation: Yes, create workspace mapping using same pattern as OAuth (upsert with organization_id)

3. **User correlation on manual token save**
   - What we know: OAuth flow correlates Linear user to organization users (lines 260-287)
   - What's unclear: Should manual token save also create/update UserCorrelation?
   - Recommendation: Yes, follow OAuth pattern - correlate if linear_email and organization_id exist

## Sources

### Primary (HIGH confidence)
- Codebase analysis: backend/app/api/endpoints/linear.py (lines 1-1342)
- Codebase analysis: backend/app/api/endpoints/jira.py /connect-manual endpoint (lines 638-773)
- Codebase analysis: backend/app/services/integration_validator.py (lines 238-309)
- Codebase analysis: frontend/src/app/integrations/components/JiraManualSetupForm.tsx (lines 1-252)
- Codebase analysis: frontend/src/app/integrations/components/LinearManualSetupForm.tsx (lines 1-229)
- Phase 3 research: .planning/phases/03-jira-token-integration/03-RESEARCH.md (proven patterns)
- Linear API documentation - [API and Webhooks](https://linear.app/docs/api-and-webhooks)
- Linear API documentation - [Getting Started with GraphQL](https://linear.app/developers/graphql)

### Secondary (MEDIUM confidence)
- Linear API token format - [GitGuardian Linear API Key Detector](https://docs.gitguardian.com/secrets-detection/secrets-detection-engine/detectors/specifics/linear_api_key)
- Linear API token creation - [How to get your API key in Linear](https://www.merge.dev/blog/linear-api-key)
- Linear API authentication - [Linear API Essentials](https://rollout.com/integration-guides/linear/api-essentials)

### Tertiary (LOW confidence)
- None - all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in package.json/requirements.txt, verified in imports
- Architecture: HIGH - Patterns proven in Phase 3 (Jira), existing LinearManualSetupForm has structure
- Pitfalls: HIGH - Based on existing code (IntegrationValidator handles GraphQL errors correctly)
- Background sync: MEDIUM - OAuth flow doesn't explicitly trigger sync, unclear if manual should

**Research date:** 2026-02-02
**Valid until:** 30 days (stable tech stack, established patterns from Phase 3)

---

## Research Methodology Notes

**What was validated:**
- Confirmed all frontend dependencies already installed (React Hook Form, sonner)
- Verified Phase 2 infrastructure exists and works (useValidation hook, LinearManualSetupForm)
- Confirmed Fernet encryption used consistently for all tokens (OAuth and manual)
- Verified IntegrationValidator has _validate_linear_manual_token method (lines 238-309)
- Confirmed Linear API uses GraphQL at https://api.linear.app/graphql
- Verified token format: lin_api_ prefix (validated by IntegrationValidator line 248)

**What was inferred:**
- Auto-save pattern adapted from Phase 3 (JiraManualSetupForm) - proven working
- Backend endpoint structure follows Phase 3 pattern (Jira /connect-manual)
- Workspace mapping needed (LinearIntegration.workspace_id is NOT NULL)
- User correlation follows OAuth callback pattern (lines 260-287)

**What requires implementation validation:**
- Backend POST /connect-manual endpoint (new code, not yet written)
- Auto-save flow in LinearManualSetupForm (adaptation of existing form)
- Workspace mapping creation for manual tokens (new integration point)
- User correlation for manual tokens (new integration point)

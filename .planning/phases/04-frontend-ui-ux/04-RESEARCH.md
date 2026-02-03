# Phase 4: Frontend UI & UX - Research

**Researched:** 2026-01-31
**Domain:** React/Next.js frontend, UI component library, API key management interface
**Confidence:** HIGH

## Summary

Research focused on understanding the existing On-Call Health frontend patterns, component library, and UI conventions to inform building an API key management interface. The frontend uses Next.js 16 with React 19, Tailwind CSS, and a comprehensive shadcn/ui component library built on Radix UI primitives.

The codebase has well-established patterns for dialogs, tables, forms, toasts, and data fetching. Key patterns include using `Dialog` components for modal interactions, grid-based table layouts (not HTML tables), the `sonner` library for toast notifications, and `react-hook-form` with Zod validation for forms. Copy-to-clipboard functionality already exists in `frontend/src/app/integrations/utils.ts`.

**Primary recommendation:** Build the API key management page at `/dashboard/api-keys` using existing UI components (Dialog, Button, Input, Card, Badge) following established patterns from the integrations page and OrganizationManagementDialog.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | ^16.1.5 | React framework | App router, server components |
| React | ^19.2.4 | UI library | Latest with concurrent features |
| Tailwind CSS | ^3.3.0 | Styling | Utility-first, matches design system |
| Radix UI | Various | Accessible primitives | All UI components built on Radix |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner | ^2.0.7 | Toast notifications | Success/error feedback |
| react-hook-form | ^7.70.0 | Form management | Complex forms with validation |
| zod | ^4.3.5 | Schema validation | Form validation with react-hook-form |
| lucide-react | ^0.562.0 | Icons | All icons in the app |
| date-fns | ^4.1.0 | Date formatting | Date display and manipulation |
| class-variance-authority | ^0.7.0 | Component variants | Button/badge variants |
| clsx + tailwind-merge | Various | Class utilities | Conditional class composition |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sonner | @radix-ui/react-toast | sonner already in use, simpler API |
| Custom table | @tanstack/react-table | Overkill for simple key list, existing patterns use grid divs |

**Installation:**
No new dependencies needed - all required libraries already installed.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/
│   └── dashboard/
│       └── api-keys/
│           └── page.tsx           # Main API keys page
├── components/
│   ├── api-keys/                  # NEW: API key specific components
│   │   ├── CreateKeyDialog.tsx    # Key creation modal
│   │   ├── KeyCreatedDialog.tsx   # Show-once full key modal
│   │   ├── RevokeKeyDialog.tsx    # Revocation confirmation
│   │   └── ApiKeyList.tsx         # Key list/table component
│   └── ui/                        # Existing shadcn components
└── hooks/
    └── useApiKeys.ts              # NEW: API key data fetching hook
```

### Pattern 1: Dialog-based Modal Flow
**What:** Use Dialog components for creation, success display, and revocation confirmation
**When to use:** All modal interactions in the app
**Example:**
```typescript
// Source: frontend/src/app/integrations/dialogs/DeleteIntegrationDialog.tsx
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"

interface RevokeKeyDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  keyName: string | null
  isRevoking: boolean
  onConfirmRevoke: () => void
  onCancel: () => void
}

export function RevokeKeyDialog({
  open,
  onOpenChange,
  keyName,
  isRevoking,
  onConfirmRevoke,
  onCancel
}: RevokeKeyDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Revoke API Key</DialogTitle>
          <DialogDescription>
            Are you sure you want to revoke "{keyName}"?
            This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirmRevoke} disabled={isRevoking}>
            {isRevoking ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Revoking...
              </>
            ) : (
              "Revoke Key"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

### Pattern 2: Grid-based Table Layout
**What:** Use CSS grid divs instead of HTML tables for data lists
**When to use:** All list/table displays in the app
**Example:**
```typescript
// Source: frontend/src/app/integrations/dialogs/OrganizationManagementDialog.tsx
<div className="border rounded-lg overflow-hidden">
  {/* Header Row */}
  <div className="bg-neutral-100 px-4 py-2 border-b">
    <div className="grid grid-cols-4 gap-4 text-sm font-medium text-neutral-700">
      <div>Name</div>
      <div>Key Prefix</div>
      <div>Created</div>
      <div>Actions</div>
    </div>
  </div>
  {/* Data Rows */}
  <div className="max-h-60 overflow-y-auto">
    {keys.map((key) => (
      <div key={key.id} className="px-4 py-3 border-b last:border-b-0 hover:bg-neutral-100">
        <div className="grid grid-cols-4 gap-4 text-sm items-center">
          <div className="font-medium">{key.name}</div>
          <div className="font-mono text-neutral-500">{key.masked_key}</div>
          <div>{formatDate(key.created_at)}</div>
          <div>
            <Button variant="destructive" size="sm">Revoke</Button>
          </div>
        </div>
      </div>
    ))}
  </div>
</div>
```

### Pattern 3: Data Fetching with localStorage Auth
**What:** Fetch data using Bearer token from localStorage
**When to use:** All authenticated API calls
**Example:**
```typescript
// Source: frontend/src/components/TeamManagementDialog.tsx
const fetchApiKeys = async () => {
  setLoading(true)
  try {
    const token = localStorage.getItem("auth_token")
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api-keys`,
      { headers: { Authorization: `Bearer ${token}` } }
    )
    if (response.ok) {
      const data = await response.json()
      setApiKeys(data)
    }
  } catch (error) {
    console.error("Error fetching API keys:", error)
    toast.error("Failed to load API keys")
  } finally {
    setLoading(false)
  }
}
```

### Pattern 4: Toast Notifications with Sonner
**What:** Use `toast` from sonner for success/error feedback
**When to use:** After API operations complete
**Example:**
```typescript
// Source: frontend/src/components/TeamManagementDialog.tsx
import { toast } from "sonner"

// Success
toast.success("API key created successfully")

// Error
toast.error("Failed to create API key")

// With custom content
toast.error(
  <span>
    Operation failed - please try again
  </span>
)
```

### Pattern 5: Copy-to-Clipboard
**What:** Use existing utility function with visual feedback
**When to use:** Copying API keys
**Example:**
```typescript
// Source: frontend/src/app/integrations/utils.ts
export async function copyToClipboard(
  text: string,
  setCopied: (copied: boolean) => void
): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  } catch (err) {
    console.error('Failed to copy: ', err)
  }
}

// Usage in component
const [copied, setCopied] = useState(false)

<Button onClick={() => copyToClipboard(apiKey, setCopied)}>
  {copied ? (
    <>
      <Check className="w-4 h-4 mr-2" />
      Copied!
    </>
  ) : (
    <>
      <Copy className="w-4 h-4 mr-2" />
      Copy Key
    </>
  )}
</Button>
```

### Anti-Patterns to Avoid
- **HTML tables:** Use grid-based divs instead - consistent with existing patterns
- **Custom toast implementation:** Use sonner which is already configured
- **Direct state for forms:** Use react-hook-form for validation
- **Inline API URLs:** Use `process.env.NEXT_PUBLIC_API_URL`
- **Missing loading states:** Always show Loader2 spinner during async operations

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toast notifications | Custom toast system | `sonner` toast() | Already configured, consistent UX |
| Copy to clipboard | navigator.clipboard directly | `copyToClipboard()` from utils.ts | Handles state feedback |
| Form validation | Manual validation | react-hook-form + zod | Type-safe, better UX |
| Confirmation dialogs | window.confirm | AlertDialog or Dialog | Styled, accessible |
| Loading spinners | Custom SVG | `Loader2` from lucide-react | Consistent with app |
| Button variants | Custom classes | `Button` with variant prop | Design system compliance |
| Date formatting | Manual string manipulation | `date-fns` format() | Already installed |

**Key insight:** The codebase has mature patterns for all UI needs. Building custom solutions would create inconsistency and maintenance burden.

## Common Pitfalls

### Pitfall 1: Showing Full Key After Dialog Close
**What goes wrong:** User closes "key created" dialog before copying, loses key forever
**Why it happens:** Dialog state resets on close
**How to avoid:**
- Require explicit acknowledgment before allowing close
- Show strong warning: "This is the only time you'll see this key"
- Consider disabling close button until user clicks "I've copied the key"
**Warning signs:** User complaints about lost keys

### Pitfall 2: Missing Auth Token Handling
**What goes wrong:** API calls fail silently with 401
**Why it happens:** Token missing or expired
**How to avoid:**
- Check `localStorage.getItem('auth_token')` exists before API calls
- Handle 401 responses by redirecting to login
- Use existing `AuthInterceptor` pattern
**Warning signs:** Blank pages, failed fetches without error messages

### Pitfall 3: Inconsistent Loading States
**What goes wrong:** User clicks button multiple times, duplicate operations
**Why it happens:** No disabled state during loading
**How to avoid:**
- Set loading state immediately on action start
- Disable action buttons while loading
- Show Loader2 spinner inside button
**Warning signs:** Duplicate API keys, double revocations

### Pitfall 4: Navigation Not Updated
**What goes wrong:** User can't find API keys page
**Why it happens:** Page exists but no link in navigation
**How to avoid:**
- Add link in TopPanel navigation
- OR add in user dropdown menu under Account Settings
- Follow existing navigation patterns
**Warning signs:** Users asking "where is API key management?"

## Code Examples

Verified patterns from official sources:

### Form with react-hook-form and Zod
```typescript
// Source: frontend/src/components/ui/form.tsx pattern
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"

const createKeySchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  expires_at: z.date().optional(),
})

type CreateKeyForm = z.infer<typeof createKeySchema>

function CreateKeyDialog() {
  const form = useForm<CreateKeyForm>({
    resolver: zodResolver(createKeySchema),
    defaultValues: { name: "" },
  })

  const onSubmit = async (data: CreateKeyForm) => {
    // API call here
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Key Name</FormLabel>
              <FormControl>
                <Input placeholder="My API Key" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </form>
    </Form>
  )
}
```

### Badge for Key Status
```typescript
// Source: frontend/src/components/ui/badge.tsx variants
import { Badge } from "@/components/ui/badge"

// Active key
<Badge variant="success">Active</Badge>

// Expiring soon
<Badge variant="warning">Expires in 7 days</Badge>

// Expired
<Badge variant="destructive">Expired</Badge>
```

### Date Picker for Expiration
```typescript
// Source: frontend/src/app/dashboard/page.tsx pattern
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { CalendarIcon } from "lucide-react"
import { format } from "date-fns"

<Popover>
  <PopoverTrigger asChild>
    <Button variant="outline">
      <CalendarIcon className="mr-2 h-4 w-4" />
      {expirationDate ? format(expirationDate, "PPP") : "No expiration"}
    </Button>
  </PopoverTrigger>
  <PopoverContent className="w-auto p-0">
    <Calendar
      mode="single"
      selected={expirationDate}
      onSelect={setExpirationDate}
      disabled={(date) => date < new Date()}
    />
  </PopoverContent>
</Popover>
```

### Masked Key Display
```typescript
// Pattern for displaying masked API keys
function MaskedKey({ prefix, suffix }: { prefix: string; suffix: string }) {
  return (
    <code className="font-mono text-sm bg-neutral-100 px-2 py-1 rounded">
      {prefix}...{suffix}
    </code>
  )
}

// Usage: och_live_****1234
<MaskedKey prefix="och_live_" suffix="1234" />
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@radix-ui/react-toast` | `sonner` | Already migrated | Simpler API, less boilerplate |
| Page router | App router (Next.js 16) | Current | Better server components |
| useState for forms | react-hook-form | Current | Type-safe validation |

**Deprecated/outdated:**
- `use-toast-simple.tsx`: Appears to be an older implementation, `sonner` is preferred
- HTML tables: Codebase consistently uses grid divs instead

## Open Questions

Things that couldn't be fully resolved:

1. **Navigation Placement**
   - What we know: TopPanel has Dashboard and Integrations links
   - What's unclear: Should API Keys be a top-level nav item or nested in user dropdown?
   - Recommendation: Add to user dropdown under "Account Settings" to keep top nav clean

2. **Key Prefix Format**
   - What we know: Requirements mention `och_live_` prefix
   - What's unclear: Should we have `och_test_` for test keys?
   - Recommendation: Start with single prefix, can extend later

## Sources

### Primary (HIGH confidence)
- `frontend/package.json` - Library versions verified
- `frontend/src/components/ui/` - All component patterns
- `frontend/src/app/integrations/dialogs/` - Dialog patterns
- `frontend/src/app/integrations/utils.ts` - Copy-to-clipboard utility
- `frontend/tailwind.config.js` - Design system colors

### Secondary (MEDIUM confidence)
- `frontend/src/components/TeamManagementDialog.tsx` - Data fetching patterns
- `frontend/src/components/mapping-drawer.tsx` - Complex form/table patterns

### Tertiary (LOW confidence)
- None - all research based on codebase analysis

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - direct package.json verification
- Architecture: HIGH - patterns verified from multiple source files
- Pitfalls: MEDIUM - inferred from codebase patterns and common React/Next.js issues

**Research date:** 2026-01-31
**Valid until:** 2026-03-01 (30 days - stable frontend patterns)

# New Relic Frontend Monitoring Setup

The frontend now includes New Relic Browser monitoring for tracking performance, errors, and user interactions.

## Setup Steps

### 1. Get New Relic Browser Application Credentials

1. Log into New Relic (https://one.newrelic.com)
2. Go to **Browser** → **+ Add more data** → **Browser monitoring**
3. Create a new browser application or select existing one
4. Choose **Copy/Paste JavaScript code** method
5. Look for the configuration object in the JavaScript snippet. You'll see something like:

```javascript
NREUM.info = {
  beacon: "bam.nr-data.net",
  errorBeacon: "bam.nr-data.net",
  licenseKey: "NRJS-xxxxxxxxxxxxx",    // ← This is NEXT_PUBLIC_NEW_RELIC_LICENSE_KEY
  applicationID: "123456789",           // ← This is NEXT_PUBLIC_NEW_RELIC_APPLICATION_ID
  sa: 1
}

NREUM.loader_config = {
  accountID: "1234567",                 // ← This is NEXT_PUBLIC_NEW_RELIC_ACCOUNT_ID
  trustKey: "1234567",                  // ← This is NEXT_PUBLIC_NEW_RELIC_TRUST_KEY
  agentID: "987654321",                 // ← This is NEXT_PUBLIC_NEW_RELIC_AGENT_ID
  licenseKey: "NRJS-xxxxxxxxxxxxx",
  applicationID: "123456789"
}
```

### 2. Add Environment Variables to Vercel

Go to your Vercel project settings and add these environment variables:

```bash
NEXT_PUBLIC_NEW_RELIC_ACCOUNT_ID=your_account_id
NEXT_PUBLIC_NEW_RELIC_TRUST_KEY=your_trust_key
NEXT_PUBLIC_NEW_RELIC_AGENT_ID=your_agent_id
NEXT_PUBLIC_NEW_RELIC_LICENSE_KEY=your_license_key
NEXT_PUBLIC_NEW_RELIC_APPLICATION_ID=your_application_id
```

**Important:**
- All variables must start with `NEXT_PUBLIC_` to be available in the browser
- Add them to all environments (Production, Preview, Development) or just Production

### 3. Redeploy

After adding the environment variables, trigger a new deployment:
- Push a commit, or
- Go to Vercel Dashboard → Deployments → Redeploy

### 4. Verify

1. Open your deployed frontend in a browser
2. Open browser DevTools → Console
3. Look for: `✅ New Relic Browser Agent initialized`
4. Go to New Relic Browser → (your app) → should see data flowing in

## What's Monitored

- **Page Load Performance:** Core Web Vitals, load times
- **AJAX Requests:** API calls to backend
- **JavaScript Errors:** Runtime errors and exceptions
- **User Sessions:** Session traces and interactions
- **Browser Types:** User agent distribution

## Graceful Fallback

If the environment variables are not set:
- The app will log: `New Relic Browser Agent: Configuration not found, skipping initialization`
- The app continues to work normally without monitoring
- No errors or crashes

## Architecture

- **`src/lib/newrelic.ts`:** Core initialization logic with dynamic import to avoid SSR issues
- **`src/components/NewRelicProvider.tsx`:** Client component that initializes on mount
- **`src/app/layout.tsx`:** Root layout wraps app with NewRelicProvider

## Testing Locally

Add the variables to `frontend/.env.local`:

```bash
NEXT_PUBLIC_NEW_RELIC_ACCOUNT_ID=...
NEXT_PUBLIC_NEW_RELIC_TRUST_KEY=...
NEXT_PUBLIC_NEW_RELIC_AGENT_ID=...
NEXT_PUBLIC_NEW_RELIC_LICENSE_KEY=...
NEXT_PUBLIC_NEW_RELIC_APPLICATION_ID=...
```

Then run `npm run dev` and check the browser console.

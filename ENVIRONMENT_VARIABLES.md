# Environment Variables Configuration

## Railway Backend (Production)

Set these in Railway dashboard → Backend service → Variables:

```bash
# Backend URL (used for OAuth redirects)
BACKEND_URL=https://rootly-burnout-detector-web-production.up.railway.app

# Frontend URL (used for CORS and redirects)
FRONTEND_URL=https://www.oncallburnout.com

# Slack OAuth credentials
SLACK_CLIENT_ID=9124300053329.9133255147168
SLACK_CLIENT_SECRET=[your-production-slack-secret]

# Database (auto-set by Railway)
DATABASE_URL=[auto-generated-by-railway]
```

## Railway Backend (Development)

Set these in Railway dashboard → Backend service → Variables (development environment):

```bash
# Backend URL (used for OAuth redirects)
BACKEND_URL=https://rootly-burnout-detector-web-development.up.railway.app

# Frontend URL (used for CORS and redirects)
FRONTEND_URL=http://localhost:3000

# Slack OAuth credentials (use development Slack app)
SLACK_CLIENT_ID=[your-dev-slack-client-id]
SLACK_CLIENT_SECRET=[your-dev-slack-secret]

# Database (auto-set by Railway)
DATABASE_URL=[auto-generated-by-railway]
```

## Vercel Frontend (Production)

Set these in Vercel dashboard → Project → Settings → Environment Variables → Production:

```bash
# Backend API URLs
NEXT_PUBLIC_API_URL=https://rootly-burnout-detector-web-production.up.railway.app
NEXT_PUBLIC_API_BASE_URL=https://rootly-burnout-detector-web-production.up.railway.app

# Slack OAuth
NEXT_PUBLIC_SLACK_CLIENT_ID=9124300053329.9133255147168
```

## Vercel Frontend (Preview/Development)

Set these in Vercel dashboard → Project → Settings → Environment Variables → Preview:

```bash
# Backend API URLs
NEXT_PUBLIC_API_URL=https://rootly-burnout-detector-web-development.up.railway.app
NEXT_PUBLIC_API_BASE_URL=https://rootly-burnout-detector-web-development.up.railway.app

# Slack OAuth
NEXT_PUBLIC_SLACK_CLIENT_ID=[your-dev-slack-client-id]
```

## Local Development (.env.local)

Create `frontend/.env.local`:

```bash
# Point to development backend
NEXT_PUBLIC_API_URL=https://rootly-burnout-detector-web-development.up.railway.app
NEXT_PUBLIC_API_BASE_URL=https://rootly-burnout-detector-web-development.up.railway.app

# Or point to local backend
# NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Slack OAuth
NEXT_PUBLIC_SLACK_CLIENT_ID=9124300053329.9133255147168
```

## Slack App Configuration

### Production Slack App
- **Redirect URLs**:
  - `https://rootly-burnout-detector-web-production.up.railway.app/integrations/slack/oauth/callback`
- **OAuth Scopes**: `commands`, `chat:write`, `team:read`

### Development Slack App (optional separate app)
- **Redirect URLs**:
  - `https://rootly-burnout-detector-web-development.up.railway.app/integrations/slack/oauth/callback`
  - `http://localhost:8000/integrations/slack/oauth/callback` (for local testing)
- **OAuth Scopes**: `commands`, `chat:write`, `team:read`

## How It Works

1. **BACKEND_URL** (Railway): Used by backend to construct OAuth redirect URI
2. **FRONTEND_URL** (Railway): Used for CORS and post-OAuth redirects
3. **NEXT_PUBLIC_API_BASE_URL** (Vercel): Used by frontend to make API calls
4. **SLACK_CLIENT_ID** (Both): Used to initiate OAuth and exchange tokens

The code now:
- Prefers `BACKEND_URL` if set (explicit configuration)
- Falls back to auto-detection from `DATABASE_URL` (checks for "production" keyword)
- Handles local development automatically

# OAuth Setup Guide for GitHub and Slack Integration

The GitHub and Slack integration buttons are now implemented and functional! However, to use them, you need to set up OAuth applications and configure the environment variables.

## ✅ Current Status
- **Frontend**: ✅ Buttons are working and will show helpful error messages
- **Backend**: ✅ OAuth endpoints are implemented with proper error handling
- **Missing**: OAuth app credentials (requires setup below)

## 🔧 Setup Required

### 1. GitHub OAuth App Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the details:
   - **Application name**: `Rootly Burnout Detector`
   - **Homepage URL**: `http://localhost:3000` (or your domain)
   - **Authorization callback URL**: `http://localhost:3000/setup/github/callback`
4. After creating, note down the **Client ID** and **Client Secret**

### 2. Slack OAuth App Setup

1. Go to [Slack API Applications](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name: `Rootly Burnout Detector`
4. Choose your workspace
5. Go to **OAuth & Permissions**:
   - Add redirect URL: `http://localhost:3000/setup/slack/callback`
   - Add these OAuth scopes:
     - `channels:history`
     - `groups:history` 
     - `users:read`
     - `search:read` (user scope)
6. Note down the **Client ID** and **Client Secret**

### 3. Environment Configuration

Create/update your `.env` file in the backend directory:

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here

# Slack OAuth  
SLACK_CLIENT_ID=your_slack_client_id_here
SLACK_CLIENT_SECRET=your_slack_client_secret_here

# Frontend URL (update if different)
FRONTEND_URL=http://localhost:3000
```

### 4. Restart Backend

After adding the environment variables, restart your backend server:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## 🚀 Testing the Integration

Once configured:

1. **Go to the integrations page** (`/integrations`)
2. **Scroll to the bottom** to see the GitHub and Slack section
3. **Click either card or button** - should redirect to OAuth authorization
4. **Complete OAuth flow** - will redirect back with authorization code
5. **Integration will be stored** and available for burnout analysis

## 🔍 Current Behavior (Without OAuth Setup)

- **Clicking buttons** → Shows helpful error message about OAuth not being configured
- **No crashes** → Graceful error handling with user-friendly messages
- **Ready to work** → As soon as OAuth credentials are added

## 🛠 Technical Details

- **OAuth endpoints**: `/integrations/github/connect` and `/integrations/slack/connect`
- **Callback URLs**: `/setup/github/callback` and `/setup/slack/callback`
- **Error handling**: Returns 503 status with helpful messages when not configured
- **Security**: Proper state parameter handling and token encryption
- **Scopes**: Minimal required permissions for burnout analysis

The integration infrastructure is complete - just needs OAuth app credentials to activate! 🎉
# 🚀 Production Deployment Guide

**Recommended Stack**: Vercel (Frontend) + Railway (Backend + Database)

This is the simplest, most reliable way to deploy the Rootly Burnout Detector in production.

## 🏗️ Architecture Overview

- **Frontend**: Next.js 14 on Vercel
- **Backend**: FastAPI + Python 3.11 on Railway
- **Database**: PostgreSQL on Railway
- **Authentication**: OAuth (Google/GitHub) + JWT tokens

### Step 1: OAuth Setup (Required)

**Google OAuth:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API  
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - `https://your-railway-app.railway.app/auth/google/callback`

**GitHub OAuth:**
1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create new OAuth App
3. Set Authorization callback URL:
   - `https://your-railway-app.railway.app/auth/github/callback`

1. **Create Railway Account**: Go to [railway.app](https://railway.app) and sign up

2. **Create New Project**: 
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Select the `backend` folder as the root directory

3. **Add PostgreSQL Database**:
   - In your Railway project, click "New Service"
   - Select "Database" > "PostgreSQL"
   - Railway will automatically create the database and connection URL

4. **Configure Environment Variables**:
   ```bash
   SECRET_KEY=your-32-character-minimum-secret-key
   DEBUG=false
   FRONTEND_URL=https://your-app.vercel.app
   
   # OAuth (from Step 1)
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GITHUB_CLIENT_ID=your-github-client-id
   GITHUB_CLIENT_SECRET=your-github-client-secret
   
   # Optional: AI features
   ANTHROPIC_API_KEY=your-anthropic-api-key
   ```

5. **Deploy**: Railway will automatically build and deploy your backend

1. **Create Vercel Account**: Go to [vercel.com](https://vercel.com) and sign up

2. **Import Project**:
   - Click "New Project"
   - Import your GitHub repository
   - Vercel will auto-detect it's a Next.js app
   - Set the root directory to `frontend`

3. **Configure Environment Variables**:
   ```bash
   NEXT_PUBLIC_API_URL=https://your-railway-app.railway.app
   NODE_ENV=production
   ```

4. **Deploy**: Vercel will automatically build and deploy your frontend

### Step 4: Connect Frontend and Backend

1. **Update Railway Environment**:
   - Go back to Railway
   - Update `FRONTEND_URL` to your Vercel URL: `https://your-app.vercel.app`

2. **Update OAuth Redirects**:
   - Google Cloud Console: Add `https://your-railway-app.railway.app/auth/google/callback`
   - GitHub OAuth App: Add `https://your-railway-app.railway.app/auth/github/callback`

3. **Test the Connection**: Visit your Vercel URL and try logging in

## 🎉 You're Done!

Your app is now live at:
- **Frontend**: `https://your-app.vercel.app`
- **Backend**: `https://your-railway-app.railway.app`
- **API Docs**: `https://your-railway-app.railway.app/docs`

## 💰 Costs (Free Tier)

**Vercel Free:**
- 100GB bandwidth/month
- Unlimited sites
- Custom domains

**Railway Free:**
- $5 credit/month
- Usually covers small apps
- PostgreSQL included

**Total**: ~$0-5/month for most use cases

## 🔄 Auto-Deployments

Both platforms will automatically redeploy when you push to your GitHub repository:
- **Frontend**: Any push to `main` branch redeploys Vercel
- **Backend**: Any push to `main` branch redeploys Railway

If you prefer to develop locally, you can still use Docker:

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your OAuth keys

# Start all services
docker-compose up --build

# Access:
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Database: localhost:5432
```

## 🔧 Troubleshooting

### Common Issues

**Backend not starting:**
- Check Railway logs in the dashboard
- Verify all environment variables are set
- Ensure OAuth redirect URLs are correct

**Frontend can't reach backend:**
- Verify `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Check CORS settings in Railway backend
- Ensure both services are deployed

**OAuth authentication fails:**
- Double-check client IDs and secrets
- Verify redirect URLs match exactly
- Ensure OAuth apps are active

### Getting Help

**Railway Issues:**
- Check Railway status page
- View deployment logs in Railway dashboard
- Use Railway's Discord community

**Vercel Issues:**
- Check Vercel status page  
- View deployment logs in Vercel dashboard
- Use Vercel's Discord community

## ✅ Production Checklist

Before going live, ensure:
- [ ] OAuth apps configured with production URLs
- [ ] Strong SECRET_KEY (32+ characters) in Railway
- [ ] Environment variables set in both Vercel and Railway  
- [ ] Custom domain configured (optional)
- [ ] Test authentication flow works
- [ ] Database backups enabled on Railway

## 💡 Tips

- **Custom Domains**: Both Vercel and Railway support custom domains
- **Monitoring**: Use Railway's built-in metrics and Vercel Analytics
- **Scaling**: Both platforms auto-scale based on usage
- **Logs**: Access logs directly in each platform's dashboard

---

That's it! Your app should now be deployed and running on Vercel + Railway. 🎉
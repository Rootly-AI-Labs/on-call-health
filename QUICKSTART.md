# ⚡ Quick Start Guide

Deploy the Rootly Burnout Detector in production in **5 minutes**.

## 🚀 Step-by-Step Deployment

### Step 1: OAuth Setup (2 minutes)

**Google OAuth** (Choose one):
1. [Google Cloud Console](https://console.cloud.google.com/) → New Project
2. APIs & Services → Enable Google+ API  
3. Credentials → Create OAuth 2.0 Client
4. Add redirect: `https://your-railway-app.railway.app/auth/google/callback`

**GitHub OAuth** (Alternative):
1. GitHub Settings → Developer Settings → OAuth Apps
2. New OAuth App
3. Callback URL: `https://your-railway-app.railway.app/auth/github/callback`

### Step 2: Deploy Backend (2 minutes)

1. **Railway**: Go to [railway.app](https://railway.app)
2. **New Project** → Deploy from GitHub → Select your repo
3. **Add Database** → PostgreSQL
4. **Connect Database**: 
   - Go to your PostgreSQL service → Variables tab
   - Copy the `DATABASE_URL` 
   - Go to your backend service → Variables tab
   - Add: `DATABASE_URL` = (paste the connection string)
5. **Environment Variables**:
   ```
   SECRET_KEY=your-random-32-character-string
   FRONTEND_URL=https://your-app.vercel.app
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=https://your-railway-app.railway.app/auth/google/callback
   GITHUB_CLIENT_ID=your-github-client-id (if using GitHub)
   GITHUB_CLIENT_SECRET=your-github-client-secret (if using GitHub)
   GITHUB_REDIRECT_URI=https://your-railway-app.railway.app/auth/github/callback
   ```

### Step 3: Deploy Frontend (1 minute)

1. **Vercel**: Go to [vercel.com](https://vercel.com)
2. **Import Project** → GitHub → Select repo → Root: `frontend`
3. **Environment Variable**:
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-app.railway.app
   ```

### Step 4: Connect & Test (30 seconds)

1. **Update Railway** `FRONTEND_URL` → Your Vercel URL
2. **Visit** your Vercel URL
3. **Test login** with Google/GitHub

## ✅ You're Live!

Your app is now running at:
- **App**: `https://your-app.vercel.app`
- **API**: `https://your-railway-app.railway.app`

## 💰 Cost
- **Free tier**: $0/month
- **Light usage**: ~$5/month

## 🔄 Updates
Both platforms auto-deploy when you push to GitHub.

## 🆘 Need Help?
See full guide: [DEPLOYMENT.md](DEPLOYMENT.md)
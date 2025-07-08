# Backend Restart Instructions

The 404 error you're seeing when testing the PagerDuty connection is likely because the backend server is not running properly. The log shows "Address already in use" error.

## To fix this:

1. **Kill any existing processes on port 8000:**
   ```bash
   lsof -ti:8000 | xargs kill -9
   ```

2. **Navigate to the backend directory:**
   ```bash
   cd /Users/spencercheng/Workspace/Rootly/rootly-burnout-detector-web/backend
   ```

3. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

4. **Start the backend server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Verify it's running:**
   ```bash
   curl http://localhost:8000/health
   ```

   You should see:
   ```json
   {"status":"healthy","service":"rootly-burnout-detector"}
   ```

## Alternative: Use a different port

If port 8000 is still in use, you can run on a different port:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Then update the frontend `.env.local` file:
```
NEXT_PUBLIC_API_URL=http://localhost:8001
```

The PagerDuty token test endpoint is correctly implemented at `/pagerduty/token/test`. Once the backend is running, it should work properly.
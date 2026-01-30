#!/bin/bash
set -e

echo "🔧 Starting Worker Process..."

# Wait for database to be available
echo "⏳ Waiting for database connection..."
python -c "
import sys
import time
import os
sys.path.insert(0, 'app')
from app.models import get_db
from sqlalchemy import text

max_attempts = 30
for attempt in range(max_attempts):
    try:
        db = next(get_db())
        db.execute(text('SELECT 1'))
        db.close()
        print('✅ Database connection successful')
        break
    except Exception as e:
        if attempt == max_attempts - 1:
            print(f'❌ Database connection failed after {max_attempts} attempts: {e}')
            sys.exit(1)
        print(f'⏳ Attempt {attempt + 1}/{max_attempts} - waiting for database...')
        time.sleep(2)
"

# Wait for Redis to be available (if configured)
if [ -n "$REDIS_URL" ] || [ -n "$ARQ_REDIS_URL" ]; then
    echo "⏳ Waiting for Redis connection..."
    python -c "
import sys
import time
import os
import redis

redis_url = os.getenv('ARQ_REDIS_URL') or os.getenv('REDIS_URL')
if redis_url:
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            r = redis.from_url(redis_url)
            r.ping()
            print('✅ Redis connection successful')
            break
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f'⚠️  Redis connection failed after {max_attempts} attempts: {e}')
                print('   Continuing without Redis...')
            else:
                print(f'⏳ Attempt {attempt + 1}/{max_attempts} - waiting for Redis...')
                time.sleep(2)
"
fi

echo "✅ Worker pre-checks completed!"
echo "🚀 Starting worker with APScheduler..."

# Start the FastAPI application (APScheduler starts automatically)
# The worker runs the same app but typically doesn't expose HTTP endpoints
exec uvicorn app.main:app --host 0.0.0.0 --port 8001

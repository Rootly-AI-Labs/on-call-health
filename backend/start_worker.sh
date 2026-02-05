#!/bin/bash
# ARQ Worker Startup Script
#
# Starts the ARQ worker process for background task processing.
# This should run alongside the FastAPI web server.

set -e

echo "🔧 Starting ARQ Worker Process..."

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

# Wait for Redis to be available (required for ARQ)
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
                print(f'❌ Redis connection failed after {max_attempts} attempts: {e}')
                print('   ARQ worker requires Redis to be running.')
                sys.exit(1)
            print(f'⏳ Attempt {attempt + 1}/{max_attempts} - waiting for Redis...')
            time.sleep(2)
else:
    print('❌ No Redis URL configured. ARQ worker requires Redis.')
    sys.exit(1)
"

echo "✅ Worker pre-checks completed!"
echo "🚀 Starting ARQ worker..."

# Run ARQ worker with the WorkerSettings class
# Worker runs continuously (default behavior, no --burst flag)
# Worker handles SIGTERM gracefully for deployment resilience
# Note: max_jobs is configured in WorkerSettings class, not via CLI
exec arq app.workers.arq_worker.WorkerSettings --verbose

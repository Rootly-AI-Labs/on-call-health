#!/bin/bash
set -e

echo "🚀 Starting Railway deployment process..."

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

# Run database migrations using simple migration runner
echo "🔄 Running database migrations..."
echo "📂 Current directory: $(pwd)"

if python simple_migration.py; then
    echo "✅ All migrations completed successfully!"
else
    echo "⚠️  Migration failed, but continuing startup..."
    echo "   Check logs above for details"
fi

# Run integration_ids column migration
echo "🔄 Running integration_ids migration..."
if python add_integration_id_to_user_correlations.py; then
    echo "✅ Integration IDs migration completed successfully!"
else
    echo "⚠️  Integration IDs migration failed, but continuing startup..."
    echo "   Check logs above for details"
fi

# Run survey message update migration
echo "🔄 Updating survey messages..."
if python update_survey_messages.py; then
    echo "✅ Survey messages updated successfully!"
else
    echo "⚠️  Survey message update failed, but continuing startup..."
    echo "   Check logs above for details"
fi

# Create tables (safe - won't recreate existing tables)
echo "🏗️  Ensuring all database tables exist..."
python -c "
import sys
sys.path.insert(0, 'app')
from app.models import create_tables
create_tables()
print('✅ Database tables verified')
"

echo "🎉 Pre-deployment setup completed successfully!"
echo "🚀 Starting FastAPI application..."

# Start the FastAPI application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
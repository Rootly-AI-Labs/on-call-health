#!/bin/bash
# ARQ Worker Startup Script
#
# Starts the ARQ worker process for background task processing.
# This should run alongside the FastAPI web server.
#
# Usage:
#   ./start_worker.sh
#
# Environment Variables:
#   ARQ_MAX_JOBS - Max concurrent jobs per worker (default: 10)

set -e

echo "Starting ARQ worker..."

ARQ_MAX_JOBS=${ARQ_MAX_JOBS:-10}

echo "Configuration:"
echo "  Max jobs per worker: $ARQ_MAX_JOBS"
echo "  Queue: analysis_queue"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if arq is installed
if ! command -v arq &> /dev/null; then
    echo "Error: ARQ not found. Install with: pip install arq"
    exit 1
fi

echo "Starting ARQ worker process..."

# Run ARQ worker with the WorkerSettings class
# Worker runs continuously (default behavior, no --burst flag)
# Worker handles SIGTERM gracefully for deployment resilience
exec arq app.workers.arq_worker.WorkerSettings \
    --verbose \
    --max-jobs "$ARQ_MAX_JOBS"

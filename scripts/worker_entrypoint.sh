#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

echo "Starting Celery worker ..."
exec uv run celery -A app worker \
    --loglevel=info \
    --concurrency=1 \
    --prefetch-multiplier=1 \
    --max-tasks-per-child=50 \
    --optimization=fair

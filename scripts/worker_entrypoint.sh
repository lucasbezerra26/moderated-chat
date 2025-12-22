#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

echo "Starting Celery worker ..."
exec uv run celery -A app worker --loglevel=info

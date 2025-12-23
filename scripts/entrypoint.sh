#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

echo "Applying database migrations ..."
uv run python manage.py migrate --noinput


if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "1" ]; then
    exec uv run python manage.py runserver 0.0.0.0:8000
else
    echo "Running collectstatic ..."
    uv run python manage.py collectstatic --noinput

    echo "Starting Gunicorn ..."
    exec uv run gunicorn app.asgi:application \
        -k uvicorn.workers.UvicornWorker \
        -w 2 \
        --threads 2 \
        -b 0.0.0.0:8000
fi

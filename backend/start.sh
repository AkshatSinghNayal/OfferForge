#!/bin/sh
set -e

echo "=== Starting Placement Tracker API ==="
echo "Running database migrations..."
python3 -m alembic upgrade head || echo "Alembic warning: migration step skipped or failed, proceeding to start server..."

PORT_TO_USE="${PORT:-8000}"
echo "Starting Uvicorn web server on port ${PORT_TO_USE}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT_TO_USE}"

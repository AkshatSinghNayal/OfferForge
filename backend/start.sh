#!/bin/sh
set -e

echo "=== Starting Placement Tracker API ==="
# Fail closed if the schema cannot be upgraded; never stamp unapplied revisions.
python3 -m alembic upgrade head

PORT_TO_USE="${PORT:-8000}"
echo "Starting Uvicorn web server on port ${PORT_TO_USE}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT_TO_USE}"

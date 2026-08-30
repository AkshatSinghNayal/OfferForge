#!/bin/sh
set -e

echo "=== Starting Placement Tracker API ==="
echo "Running database migrations..."
# Fail the deployment if schema upgrades fail. Starting against an older
# schema would make newly deployed endpoints fail at runtime and hide the
# actual migration error in startup logs.
python3 -m alembic upgrade head

PORT_TO_USE="${PORT:-8000}"
echo "Starting Uvicorn web server on port ${PORT_TO_USE}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT_TO_USE}"

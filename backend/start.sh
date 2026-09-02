#!/bin/sh
set -e

echo "=== Starting Placement Tracker API ==="
# Run database migrations. If alembic upgrade fails (e.g. stale/missing revision 0008 in DB), stamp head.
if ! python3 -m alembic upgrade head; then
  echo "Alembic upgrade failed due to stale revision. Stamping database to head..."
  python3 -m alembic stamp head
fi

PORT_TO_USE="${PORT:-8000}"
echo "Starting Uvicorn web server on port ${PORT_TO_USE}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT_TO_USE}"

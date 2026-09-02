#!/bin/sh
set -e

echo "=== Starting Placement Tracker API ==="
# Run database migrations. If alembic upgrade fails (e.g. invalid revision 0008 in DB), purge and stamp head.
if ! python3 -m alembic upgrade head; then
  echo "Alembic upgrade failed due to stale revision. Purging and stamping database to head..."
  python3 -m alembic stamp --purge head || python3 -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def fix():
    url = os.environ.get('DATABASE_URL', '').replace('postgresql://', 'postgresql+asyncpg://')
    if url:
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.execute(text('TRUNCATE alembic_version;'))
            await conn.execute(text(\"INSERT INTO alembic_version (version_num) VALUES ('0007_reconcile_job_match_table');\"))
        await engine.dispose()
asyncio.run(fix())
"
  python3 -m alembic upgrade head || true
fi

PORT_TO_USE="${PORT:-8000}"
echo "Starting Uvicorn web server on port ${PORT_TO_USE}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT_TO_USE}"

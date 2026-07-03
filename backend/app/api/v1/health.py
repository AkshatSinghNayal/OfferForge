"""Health endpoint — intentionally public, no auth.

Used by:
  - docker-compose healthcheck
  - Render uptime monitor
  - CI smoke test
  - Frontend boot check

Returns 200 with a small JSON body when the FastAPI process is up AND the
database is reachable. Returns 503 if the DB is unreachable so the load
balancer can pull the instance out of rotation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session

router = APIRouter()


@router.get("/health")
async def health(session: AsyncSession = Depends(get_async_session)) -> JSONResponse:
    """Liveness + DB-readiness probe."""
    try:
        # Cheap round-trip. If this raises, the DB is down.
        result = await session.execute(text("SELECT 1"))
        result.scalar_one()
        db_ok = True
    except Exception:
        db_ok = False

    body = {"status": "ok" if db_ok else "degraded", "db": "ok" if db_ok else "unreachable"}
    code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=body)

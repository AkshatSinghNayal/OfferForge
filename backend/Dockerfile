# Backend Dockerfile — FastAPI + uvicorn.
# Multi-stage not strictly necessary at this size, but we keep build + runtime
# separate so the final image doesn't ship pip cache / build tools.

FROM python:3.11-slim AS builder

# Build deps for asyncpg / bcrypt / cryptography wheels when no prebuilt
# wheel is available for the target arch.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------- runtime
FROM python:3.11-slim AS runtime

# Runtime deps: libpq for asyncpg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder.
COPY --from=builder /install /usr/local

# Copy application code.
COPY . .

# Expose FastAPI default port.
EXPOSE 8000

# Run alembic migrations on container start, then boot uvicorn.
# In production we recommend running migrations as a separate Release command
# on Render, but for local docker-compose this entrypoint keeps things simple.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

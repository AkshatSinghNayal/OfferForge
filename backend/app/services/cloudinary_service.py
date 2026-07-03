"""Cloudinary integration — PDF upload + destroy.

Supports two credential formats:
  1. CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name  (single env var)
  2. CLOUDINARY_CLOUD_NAME + CLOUDINARY_API_KEY + CLOUDINARY_API_SECRET (three vars)

Falls back to local /tmp storage when no credentials are configured (dev/test).
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings


LOCAL_STORAGE_DIR = Path("/tmp/placement-tracker-resumes")


class CloudinaryError(Exception):
    """Raised on any upload/destroy failure."""


def _get_cloudinary_config() -> tuple[str, str, str] | None:
    """Return (cloud_name, api_key, api_secret) or None if not configured.

    Checks CLOUDINARY_URL first (cloudinary://api_key:api_secret@cloud_name),
    then falls back to the three individual env vars.
    """
    # 1. Parse CLOUDINARY_URL
    if settings.CLOUDINARY_URL:
        try:
            parsed = urlparse(settings.CLOUDINARY_URL)
            cloud_name = parsed.hostname or ""
            api_key = parsed.username or ""
            api_secret = parsed.password or ""
            if cloud_name and api_key and api_secret:
                return cloud_name, api_key, api_secret
        except Exception:
            pass

    # 2. Individual vars
    if (settings.CLOUDINARY_CLOUD_NAME
            and settings.CLOUDINARY_API_KEY
            and settings.CLOUDINARY_API_SECRET):
        return (
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        )

    return None


async def upload_pdf(file_bytes: bytes, filename: str, *, folder: str = "resumes") -> tuple[str, str]:
    """Upload a PDF to Cloudinary. Returns (secure_url, public_id).

    Falls back to local /tmp storage when no Cloudinary credentials are set.
    """
    creds = _get_cloudinary_config()
    if not creds:
        return await _upload_local(file_bytes, filename)

    cloud_name, api_key, api_secret = creds

    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError as e:
        raise CloudinaryError(f"cloudinary SDK not installed: {e}") from e

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )

    public_id = f"{folder}/{uuid.uuid4().hex}"
    # Pass a base64 data URI instead of a BytesIO object.  The Cloudinary SDK
    # reads a file-like object to probe its size, advancing the cursor, then
    # may not seek back before the actual upload — sending 0 bytes.  Data URIs
    # are an explicitly supported source type and bypass that code path entirely.
    data_uri = f"data:application/pdf;base64,{base64.b64encode(file_bytes).decode()}"

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: cloudinary.uploader.upload(
                data_uri,
                public_id=public_id,
                resource_type="raw",
                format="pdf",
            ),
        )
        return result["secure_url"], result["public_id"]
    except Exception as e:
        raise CloudinaryError(f"Cloudinary upload failed: {e}") from e


async def destroy_file(public_id: str) -> None:
    """Delete a file from Cloudinary. Best-effort — never raises."""
    creds = _get_cloudinary_config()
    if not creds:
        _destroy_local(public_id)
        return

    cloud_name, api_key, api_secret = creds

    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )
        cloudinary.uploader.destroy(public_id, resource_type="raw")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Local fallback
# ---------------------------------------------------------------------------

async def _upload_local(file_bytes: bytes, filename: str) -> tuple[str, str]:
    LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    public_id = f"resumes/{uuid.uuid4().hex}.pdf"
    local_path = LOCAL_STORAGE_DIR / public_id.replace("/", "_")
    local_path.write_bytes(file_bytes)
    return f"file://{local_path}", public_id


def _destroy_local(public_id: str) -> None:
    local_path = LOCAL_STORAGE_DIR / public_id.replace("/", "_")
    try:
        local_path.unlink(missing_ok=True)
    except Exception:
        pass

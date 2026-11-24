"""
Where uploaded PDFs are kept.

- Locally (the default): files in UPLOAD_DIR. Fine on your own computer, but hosts like
  Render wipe the disk on every restart and deploy.
- Supabase Storage: used when SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set. Files
  go into a private bucket (SUPABASE_STORAGE_BUCKET, created on startup) that only this
  server can read, using the service role key.

Document.file_path records where each file lives: a local path, or
``supabase://<bucket>/<key>`` for Supabase. Documents uploaded before switching keep
working from wherever they were stored.
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional
from urllib.parse import quote

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

SUPABASE_PREFIX = "supabase://"

# Tests swap this for a client backed by httpx.MockTransport.
def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10))


class StorageError(Exception):
    """The file store could not be reached or refused the request."""


def uses_supabase() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


# --------------------------------------------------------------------------- #
# Supabase Storage REST API
# --------------------------------------------------------------------------- #

def _headers(**extra: str) -> dict:
    key = settings.supabase_service_role_key
    return {"apikey": key, "Authorization": f"Bearer {key}", **extra}


def _api(path: str) -> str:
    return f"{settings.supabase_base_url}/storage/v1/{path}"


def _object_url(bucket: str, key: str) -> str:
    return _api(f"object/{quote(bucket)}/{quote(key)}")


def _split(stored: str) -> tuple[str, str]:
    bucket, _, key = stored[len(SUPABASE_PREFIX):].partition("/")
    return bucket, key


async def ensure_bucket() -> None:
    """Create the private documents bucket if it doesn't exist yet (run at startup)."""
    if not uses_supabase():
        return
    bucket = settings.supabase_storage_bucket
    try:
        async with _client() as client:
            found = await client.get(_api(f"bucket/{quote(bucket)}"), headers=_headers())
            if found.status_code == 200:
                return
            created = await client.post(
                _api("bucket"),
                headers=_headers(),
                json={
                    "id": bucket,
                    "name": bucket,
                    "public": False,
                    "file_size_limit": settings.max_upload_size_bytes,
                    "allowed_mime_types": ["application/pdf"],
                },
            )
        # 409/400 "already exists" means another instance created it first.
        if created.status_code not in (200, 201) and "already exists" not in created.text.lower():
            logger.error("Could not create Supabase Storage bucket", status=created.status_code, body=created.text[:300])
        else:
            logger.info("Created Supabase Storage bucket", bucket=bucket)
    except httpx.HTTPError as exc:
        logger.error("Supabase Storage unreachable at startup", error=str(exc))


# --------------------------------------------------------------------------- #
# Operations used by the app
# --------------------------------------------------------------------------- #

async def save(content: bytes, filename: str) -> str:
    """Store an uploaded PDF and return the value to keep in Document.file_path."""
    if not uses_supabase():
        upload_dir = Path(settings.upload_dir).resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / filename
        await asyncio.to_thread(path.write_bytes, content)
        return str(path)

    bucket = settings.supabase_storage_bucket
    # Storage keys must be plain ASCII; the random part keeps same-named uploads apart.
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("_") or "document.pdf"
    key = f"{uuid.uuid4().hex[:12]}_{safe}"
    try:
        async with _client() as client:
            response = await client.post(
                _object_url(bucket, key),
                headers=_headers(**{"Content-Type": "application/pdf", "x-upsert": "false"}),
                content=content,
            )
    except httpx.HTTPError as exc:
        raise StorageError(str(exc)) from exc
    if response.status_code not in (200, 201):
        logger.error("Supabase Storage upload failed", status=response.status_code, body=response.text[:300])
        raise StorageError(f"Upload failed ({response.status_code})")
    return f"{SUPABASE_PREFIX}{bucket}/{key}"


def local_path(stored: str) -> str:
    """The on-disk path for a locally stored file (tolerates legacy relative values)."""
    if os.path.isabs(stored):
        return stored
    return os.path.join(os.path.abspath(settings.upload_dir), os.path.basename(stored))


async def open_stream(stored: str) -> Optional[AsyncIterator[bytes]]:
    """Stream a stored file's bytes, or None if it is missing."""
    if not stored.startswith(SUPABASE_PREFIX):
        path = local_path(stored)
        if not os.path.exists(path):
            return None

        async def read_local() -> AsyncIterator[bytes]:
            with open(path, "rb") as f:
                while chunk := await asyncio.to_thread(f.read, 1024 * 256):
                    yield chunk

        return read_local()

    bucket, key = _split(stored)
    client = _client()
    try:
        response = await client.send(client.build_request("GET", _object_url(bucket, key), headers=_headers()), stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise StorageError(str(exc)) from exc
    if response.status_code != 200:
        await response.aclose()
        await client.aclose()
        # Supabase answers 400 "Object not found" as well as 404.
        if response.status_code in (400, 404):
            return None
        raise StorageError(f"Download failed ({response.status_code})")

    async def read_remote() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return read_remote()


@asynccontextmanager
async def local_copy(stored: str) -> AsyncIterator[Optional[str]]:
    """A filesystem path for the PDF (downloaded to a temp file if remote), or None if missing."""
    if not stored.startswith(SUPABASE_PREFIX):
        path = local_path(stored)
        yield path if os.path.exists(path) else None
        return

    stream = await open_stream(stored)
    if stream is None:
        yield None
        return
    fd, tmp = tempfile.mkstemp(suffix=".pdf", prefix="quizzr-")
    try:
        with os.fdopen(fd, "wb") as f:
            async for chunk in stream:
                f.write(chunk)
        yield tmp
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


async def delete(stored: Optional[str]) -> None:
    """Remove a stored file. Missing files are fine; failures are logged, not raised."""
    if not stored:
        return
    if not stored.startswith(SUPABASE_PREFIX):
        try:
            os.remove(local_path(stored))
        except OSError:
            pass
        return
    await delete_many([stored])


async def delete_many(stored_paths: list[str]) -> None:
    remote: dict[str, list[str]] = {}
    for stored in stored_paths:
        if not stored:
            continue
        if stored.startswith(SUPABASE_PREFIX):
            bucket, key = _split(stored)
            remote.setdefault(bucket, []).append(key)
        else:
            await delete(stored)
    if not remote or not settings.supabase_service_role_key:
        return
    try:
        async with _client() as client:
            for bucket, keys in remote.items():
                for start in range(0, len(keys), 1000):  # API limit per request
                    response = await client.request(
                        "DELETE",
                        _api(f"object/{quote(bucket)}"),
                        headers=_headers(),
                        json={"prefixes": keys[start:start + 1000]},
                    )
                    if response.status_code != 200:
                        logger.error("Supabase Storage delete failed", status=response.status_code, body=response.text[:300])
    except httpx.HTTPError as exc:
        logger.error("Supabase Storage delete failed", error=str(exc))

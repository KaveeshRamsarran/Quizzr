"""Uploaded PDFs in Supabase Storage, against an in-memory fake of its REST API."""

import json
from urllib.parse import unquote

import httpx
import pytest
from httpx import AsyncClient

from app.config import settings
from app.services import storage
from tests.test_generation import NOTES, make_pdf

SUPABASE_URL = "https://example-project.supabase.co"
SERVICE_KEY = "service-role-key"


class FakeStorage:
    """Just enough of /storage/v1 to exercise Quizzr's calls."""

    def __init__(self):
        self.buckets: dict[str, dict] = {}
        self.objects: dict[tuple[str, str], bytes] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == f"Bearer {SERVICE_KEY}"
        path = unquote(request.url.path.removeprefix("/storage/v1/"))
        kind, _, rest = path.partition("/")
        if kind == "bucket":
            if request.method == "GET":
                return httpx.Response(200, json=self.buckets[rest]) if rest in self.buckets else httpx.Response(400, json={"error": "Bucket not found"})
            body = json.loads(request.content)
            self.buckets[body["id"]] = body
            return httpx.Response(200, json={"name": body["id"]})
        bucket, _, key = rest.partition("/")
        if request.method == "POST":
            if (bucket, key) in self.objects:
                return httpx.Response(400, json={"error": "Duplicate"})
            self.objects[(bucket, key)] = request.content
            return httpx.Response(200, json={"Key": f"{bucket}/{key}"})
        if request.method == "GET":
            data = self.objects.get((bucket, key))
            return httpx.Response(200, content=data) if data is not None else httpx.Response(400, json={"error": "Object not found"})
        if request.method == "DELETE":
            for k in json.loads(request.content)["prefixes"]:
                self.objects.pop((bucket, k), None)
            return httpx.Response(200, json=[])
        return httpx.Response(405)


@pytest.fixture
def fake_storage(monkeypatch):
    fake = FakeStorage()
    monkeypatch.setattr(settings, "supabase_url", SUPABASE_URL)
    monkeypatch.setattr(settings, "supabase_service_role_key", SERVICE_KEY)
    monkeypatch.setattr(settings, "supabase_storage_bucket", "documents")
    # Sign-in stays on built-in accounts here (no anon key), so only storage changes.
    monkeypatch.setattr(settings, "supabase_anon_key", "")
    monkeypatch.setattr(storage, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(fake.handler)))
    return fake


@pytest.mark.asyncio
async def test_bucket_is_created_private(fake_storage):
    await storage.ensure_bucket()
    assert fake_storage.buckets["documents"]["public"] is False
    assert fake_storage.buckets["documents"]["allowed_mime_types"] == ["application/pdf"]
    await storage.ensure_bucket()  # second start: already there


@pytest.mark.asyncio
async def test_upload_process_download_delete(client: AsyncClient, authenticated_user: dict, fake_storage, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    h = authenticated_user["headers"]
    pdf = make_pdf(NOTES)

    r = await client.post("/api/v1/documents/upload", files={"file": ("Cell Biology é.pdf", pdf, "application/pdf")}, headers=h)
    assert r.status_code in (200, 201), r.text
    doc_id = r.json()["id"]

    # Stored in the bucket, not on disk, under an ASCII-only key.
    assert list(tmp_path.iterdir()) == []
    [(bucket, key)] = fake_storage.objects
    assert bucket == "documents" and key.isascii() and key.endswith(".pdf")

    # Processing read it back from storage.
    doc = (await client.get(f"/api/v1/documents/{doc_id}", headers=h)).json()
    assert doc["status"] == "processed", doc
    assert doc["page_count"] >= 1

    file = await client.get(f"/api/v1/documents/{doc_id}/file", headers=h)
    assert file.status_code == 200
    assert file.content == pdf
    assert file.headers["content-type"] == "application/pdf"
    assert "filename*=UTF-8''Cell%20Biology%20%C3%A9.pdf" in file.headers["content-disposition"]

    assert (await client.delete(f"/api/v1/documents/{doc_id}", headers=h)).status_code in (200, 204)
    assert fake_storage.objects == {}


@pytest.mark.asyncio
async def test_missing_object_reports_cleanly(client: AsyncClient, authenticated_user: dict, fake_storage):
    h = authenticated_user["headers"]
    r = await client.post("/api/v1/documents/upload", files={"file": ("notes.pdf", make_pdf(NOTES), "application/pdf")}, headers=h)
    doc_id = r.json()["id"]
    fake_storage.objects.clear()
    assert (await client.get(f"/api/v1/documents/{doc_id}/file", headers=h)).status_code == 404

    reprocess = await client.post(f"/api/v1/documents/{doc_id}/reprocess", headers=h)
    assert reprocess.status_code in (200, 202)
    doc = (await client.get(f"/api/v1/documents/{doc_id}", headers=h)).json()
    assert doc["status"] == "error"
    assert "missing from storage" in (doc.get("processing_error") or "")


@pytest.mark.asyncio
async def test_account_deletion_removes_files(client: AsyncClient, authenticated_user: dict, fake_storage):
    h = authenticated_user["headers"]
    await client.post("/api/v1/documents/upload", files={"file": ("notes.pdf", make_pdf(NOTES), "application/pdf")}, headers=h)
    assert len(fake_storage.objects) == 1
    assert (await client.delete("/api/v1/auth/me", headers=h)).status_code == 204
    assert fake_storage.objects == {}


@pytest.mark.asyncio
async def test_upload_fails_cleanly_when_storage_is_down(client: AsyncClient, authenticated_user: dict, fake_storage, monkeypatch):
    def down(request):
        raise httpx.ConnectError("unreachable")
    monkeypatch.setattr(storage, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(down)))
    r = await client.post("/api/v1/documents/upload", files={"file": ("notes.pdf", make_pdf(NOTES), "application/pdf")}, headers=authenticated_user["headers"])
    assert r.status_code == 503
    docs = (await client.get("/api/v1/documents", headers=authenticated_user["headers"])).json()
    assert docs["total"] == 0

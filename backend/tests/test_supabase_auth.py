"""Sign-in through Supabase Auth: token checks, first-sign-in provisioning, guest upgrade."""

import time
import uuid

import jwt
import pytest
from httpx import AsyncClient

from app.config import settings

SUPABASE_URL = "https://example-project.supabase.co"
SECRET = "test-supabase-jwt-secret-at-least-32-characters"


@pytest.fixture
def supabase(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", SUPABASE_URL)
    monkeypatch.setattr(settings, "supabase_anon_key", "public-anon-key")
    monkeypatch.setattr(settings, "supabase_jwt_secret", SECRET)
    monkeypatch.setattr(settings, "supabase_service_role_key", "")
    monkeypatch.setattr(settings, "supabase_oauth_providers", "google")


def token(sub=None, email="ada@example.com", name="Ada Lovelace", anonymous=False, verified=True, **overrides):
    now = int(time.time())
    claims = {
        "sub": sub or str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": f"{SUPABASE_URL}/auth/v1",
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
        "email": "" if anonymous else email,
        "is_anonymous": anonymous,
        "user_metadata": {} if anonymous else {"name": name, "email_verified": verified},
    }
    claims.update(overrides)
    return jwt.encode(claims, SECRET, algorithm="HS256")


def bearer(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.mark.asyncio
async def test_config_reports_supabase(client: AsyncClient, supabase):
    data = (await client.get("/api/v1/auth/config")).json()
    assert data == {
        "provider": "supabase",
        "supabase_url": SUPABASE_URL,
        "supabase_anon_key": "public-anon-key",
        "oauth_providers": ["google"],
    }


@pytest.mark.asyncio
async def test_config_reports_builtin_by_default(client: AsyncClient):
    assert (await client.get("/api/v1/auth/config")).json() == {"provider": "builtin"}


@pytest.mark.asyncio
async def test_first_request_creates_profile_once(client: AsyncClient, supabase):
    sub = str(uuid.uuid4())
    first = await client.get("/api/v1/auth/me", headers=bearer(token(sub)))
    assert first.status_code == 200
    me = first.json()
    assert me["email"] == "ada@example.com"
    assert me["name"] == "Ada Lovelace"
    assert me["is_guest"] is False
    assert me["is_verified"] is True

    again = await client.get("/api/v1/auth/me", headers=bearer(token(sub)))
    assert again.json()["id"] == me["id"]


@pytest.mark.asyncio
async def test_rejects_bad_tokens(client: AsyncClient, supabase):
    now = int(time.time())
    bad = [
        jwt.encode({"sub": "x", "aud": "authenticated", "iss": f"{SUPABASE_URL}/auth/v1", "exp": now + 60}, "wrong-secret-wrong-secret-wrong-secret", algorithm="HS256"),
        token(exp=now - 10),
        token(aud="anon"),
        token(iss="https://other.supabase.co/auth/v1"),
        "not-a-jwt",
    ]
    for t in bad:
        assert (await client.get("/api/v1/auth/me", headers=bearer(t))).status_code == 401


@pytest.mark.asyncio
async def test_builtin_password_endpoints_are_off(client: AsyncClient, supabase):
    body = {"email": "a@example.com", "password": "password123", "name": "A"}
    assert (await client.post("/api/v1/auth/register", json=body)).status_code == 404
    assert (await client.post("/api/v1/auth/login", json=body)).status_code == 404
    assert (await client.post("/api/v1/auth/guest")).status_code == 404


@pytest.mark.asyncio
async def test_builtin_tokens_are_not_accepted(client: AsyncClient, authenticated_user, supabase):
    assert (await client.get("/api/v1/auth/me", headers=authenticated_user["headers"])).status_code == 401


@pytest.mark.asyncio
async def test_anonymous_guest_upgrades_in_place(client: AsyncClient, supabase):
    sub = str(uuid.uuid4())
    guest = (await client.get("/api/v1/auth/me", headers=bearer(token(sub, anonymous=True)))).json()
    assert guest["is_guest"] is True
    deck = await client.post("/api/v1/decks", json={"name": "Biology"}, headers=bearer(token(sub, anonymous=True)))
    assert deck.status_code in (200, 201)

    # Same Supabase user after linking an email: same Quizzr account, now standard.
    upgraded = (await client.get("/api/v1/auth/me", headers=bearer(token(sub, email="grace@example.com", name="Grace")))).json()
    assert upgraded["id"] == guest["id"]
    assert upgraded["is_guest"] is False
    assert upgraded["email"] == "grace@example.com"
    assert upgraded["name"] == "Grace"
    decks = (await client.get("/api/v1/decks", headers=bearer(token(sub, email="grace@example.com")))).json()
    assert [d["name"] for d in decks["decks"]] == ["Biology"]


@pytest.mark.asyncio
async def test_existing_account_is_linked_only_after_email_confirmation(client: AsyncClient, authenticated_user, supabase):
    email = authenticated_user["user"]["email"]
    unconfirmed = await client.get("/api/v1/auth/me", headers=bearer(token(email=email, verified=False)))
    assert unconfirmed.status_code == 409

    linked = await client.get("/api/v1/auth/me", headers=bearer(token(email=email, verified=True)))
    assert linked.status_code == 200
    assert linked.json()["id"] == authenticated_user["user"]["id"]


@pytest.mark.asyncio
async def test_email_change_must_go_through_supabase(client: AsyncClient, supabase):
    headers = bearer(token())
    assert (await client.put("/api/v1/auth/me", json={"name": "Ada L."}, headers=headers)).status_code == 200
    assert (await client.put("/api/v1/auth/me", json={"email": "new@example.com"}, headers=headers)).status_code == 400


@pytest.mark.asyncio
async def test_delete_account(client: AsyncClient, supabase):
    headers = bearer(token())
    await client.post("/api/v1/decks", json={"name": "Chemistry"}, headers=headers)
    assert (await client.delete("/api/v1/auth/me", headers=headers)).status_code == 204
    # Without a service role key the Supabase user remains; signing in again starts empty.
    assert (await client.get("/api/v1/decks", headers=headers)).json()["decks"] == []

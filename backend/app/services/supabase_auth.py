"""
Supabase Auth integration.

When Supabase is configured, the browser signs users up and in with supabase-js and
sends the Supabase access token to this API. This module verifies that token and
finds (or creates) the matching Quizzr user row, keyed by the token's ``sub``.

Tokens are verified locally: asymmetric keys (ES256/RS256) come from the project's
JWKS endpoint, and projects still on the legacy shared secret use SUPABASE_JWT_SECRET.
"""

import asyncio
from datetime import datetime
from typing import Optional

import httpx
import jwt
import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserRole

logger = structlog.get_logger()

# Placeholder stored in hashed_password for Supabase users: it is not a bcrypt hash,
# so no password ever matches it.
UNUSABLE_PASSWORD = "!supabase"

_jwks_client: Optional[jwt.PyJWKClient] = None
_jwks_url: Optional[str] = None


class AuthUnavailable(Exception):
    """Supabase's signing keys could not be fetched (network or outage)."""


def _jwks() -> jwt.PyJWKClient:
    global _jwks_client, _jwks_url
    url = f"{settings.supabase_base_url}/auth/v1/.well-known/jwks.json"
    if _jwks_client is None or _jwks_url != url:
        _jwks_client = jwt.PyJWKClient(url, cache_keys=True, lifespan=3600, timeout=10)
        _jwks_url = url
    return _jwks_client


async def verify_supabase_token(token: str) -> Optional[dict]:
    """Return the token's claims if it is a valid Supabase user access token."""
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError:
        return None

    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            return None
        key = settings.supabase_jwt_secret
    elif alg in {"ES256", "RS256"}:
        try:
            key = (await asyncio.to_thread(_jwks().get_signing_key_from_jwt, token)).key
        except jwt.PyJWKClientConnectionError as exc:
            raise AuthUnavailable(str(exc)) from exc
        except jwt.PyJWTError:
            return None
    else:
        return None

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience="authenticated",
            issuer=f"{settings.supabase_base_url}/auth/v1",
        )
    except jwt.PyJWTError:
        return None
    return claims if claims.get("sub") else None


def _profile_from_claims(claims: dict) -> dict:
    meta = claims.get("user_metadata") or {}
    is_anonymous = bool(claims.get("is_anonymous"))
    email = (claims.get("email") or "").strip().lower() or None
    name = str(meta.get("name") or meta.get("full_name") or "").strip()[:255]
    if not name and email:
        name = email.split("@")[0][:255]
    return {
        "sub": claims["sub"],
        "is_anonymous": is_anonymous or not email,
        "email": email,
        "name": name,
        "email_verified": meta.get("email_verified") is True,
    }


async def _user_by(session: AsyncSession, column, value) -> Optional[User]:
    result = await session.execute(select(User).where(column == value))
    return result.scalar_one_or_none()


async def get_or_create_user(session: AsyncSession, claims: dict) -> User:
    """Find the Quizzr user for a verified Supabase token, creating it on first sign-in."""
    profile = _profile_from_claims(claims)
    user = await _user_by(session, User.supabase_id, profile["sub"])
    if user is not None:
        await _sync_profile(session, user, profile)
        return user

    if not profile["is_anonymous"]:
        existing = await _user_by(session, User.email, profile["email"])
        if existing is not None:
            # An account made before Supabase sign-in was turned on: adopt it, but only
            # once Supabase has confirmed the address belongs to this person.
            if existing.supabase_id is None and profile["email_verified"]:
                existing.supabase_id = profile["sub"]
                existing.is_verified = True
                existing.last_login = datetime.utcnow()
                await session.commit()
                return existing
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Confirm your email address, then sign in again.",
            )

    sub = profile["sub"]
    user = User(
        supabase_id=sub,
        email=profile["email"] if not profile["is_anonymous"] else f"guest_{sub}@quizzr.temp",
        hashed_password=UNUSABLE_PASSWORD,
        name=profile["name"] if not profile["is_anonymous"] else f"Guest {sub[:6]}",
        role=UserRole.GUEST if profile["is_anonymous"] else UserRole.STANDARD,
        is_active=True,
        is_verified=profile["email_verified"],
        last_login=datetime.utcnow(),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        # Two first requests raced; the other one created the row.
        await session.rollback()
        user = await _user_by(session, User.supabase_id, sub)
        if user is None:
            raise
    return user


async def _sync_profile(session: AsyncSession, user: User, profile: dict) -> None:
    """Carry changes made in Supabase (guest upgraded, email changed) over to Quizzr."""
    changed = False
    if not profile["is_anonymous"]:
        if user.role == UserRole.GUEST:
            user.role = UserRole.STANDARD
            if profile["name"]:
                user.name = profile["name"]
            changed = True
        if profile["email"] != user.email and await _user_by(session, User.email, profile["email"]) is None:
            user.email = profile["email"]
            changed = True
        if profile["email_verified"] and not user.is_verified:
            user.is_verified = True
            changed = True
    if changed:
        user.updated_at = datetime.utcnow()
        await session.commit()


async def delete_supabase_user(supabase_id: str) -> None:
    """Remove the user from Supabase Auth. Needs SUPABASE_SERVICE_ROLE_KEY; no-op without it."""
    key = settings.supabase_service_role_key
    if not key:
        return
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.delete(
            f"{settings.supabase_base_url}/auth/v1/admin/users/{supabase_id}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
    if response.status_code not in (200, 204, 404):
        logger.error("Supabase user deletion failed", status=response.status_code, body=response.text[:500])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn’t delete your sign-in. Nothing was removed; try again.",
        )


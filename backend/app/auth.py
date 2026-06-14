"""Auth and Clerk sync helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

import jwt
import requests
from flask import current_app, g, jsonify, request
from svix.webhooks import Webhook

from .config import Config
from .db.models import User
from .runtime_settings import RuntimeSettingsService


@dataclass
class ClerkIdentity:
    clerk_user_id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    last_sign_in_at: datetime | None = None


def _normalize_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        as_int = int(value)
    except (TypeError, ValueError):
        return None
    if as_int > 10_000_000_000:
        return datetime.fromtimestamp(as_int / 1000, tz=timezone.utc)
    return datetime.fromtimestamp(as_int, tz=timezone.utc)


def _extract_email(payload: dict[str, Any]) -> str:
    if payload.get("email"):
        return payload["email"]
    for address in payload.get("email_addresses", []):
        if address.get("id") == payload.get("primary_email_address_id"):
            return address.get("email_address", "")
    if payload.get("email_addresses"):
        return payload["email_addresses"][0].get("email_address", "")
    return ""


def build_identity_from_claims(claims: dict[str, Any]) -> ClerkIdentity:
    return ClerkIdentity(
        clerk_user_id=claims["sub"],
        email=_extract_email(claims),
        first_name=claims.get("given_name") or claims.get("first_name"),
        last_name=claims.get("family_name") or claims.get("last_name"),
        avatar_url=claims.get("picture") or claims.get("image_url"),
        last_sign_in_at=_normalize_timestamp(claims.get("iat")),
    )


def build_identity_from_webhook(payload: dict[str, Any]) -> ClerkIdentity:
    data = payload.get("data", payload)
    return ClerkIdentity(
        clerk_user_id=data["id"],
        email=_extract_email(data),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        avatar_url=data.get("image_url"),
        last_sign_in_at=_normalize_timestamp(data.get("last_sign_in_at")),
    )


def sync_user(identity: ClerkIdentity, db_session, *, reactivate: bool = True) -> User:
    user = User.query.filter_by(clerk_user_id=identity.clerk_user_id).one_or_none()
    if user is None:
        user = User(
            clerk_user_id=identity.clerk_user_id,
            email=identity.email,
            first_name=identity.first_name,
            last_name=identity.last_name,
            avatar_url=identity.avatar_url,
            is_admin=False,
            is_active=True,
            last_sign_in_at=identity.last_sign_in_at,
            deleted_at=None,
        )
        db_session.session.add(user)
    else:
        user.email = identity.email
        user.first_name = identity.first_name
        user.last_name = identity.last_name
        user.avatar_url = identity.avatar_url
        user.last_sign_in_at = identity.last_sign_in_at
        if reactivate:
            user.is_active = True
            user.deleted_at = None
    db_session.session.commit()
    return user


def deactivate_user(clerk_user_id: str, db_session) -> None:
    user = User.query.filter_by(clerk_user_id=clerk_user_id).one_or_none()
    if user is None:
        return
    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)
    db_session.session.commit()


def _fetch_jwks() -> dict[str, Any]:
    response = requests.get(Config.CLERK_JWKS_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def verify_session_token(token: str) -> dict[str, Any]:
    signing_key = jwt.PyJWKClient(Config.CLERK_JWKS_URL).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


def load_current_user(db_session) -> User:
    if hasattr(g, "current_user"):
        return g.current_user
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise PermissionError("Missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    claims = verify_session_token(token)
    identity = build_identity_from_claims(claims)
    user = sync_user(identity, db_session)
    g.current_user = user
    return user


def require_user(db_session) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                user = load_current_user(db_session)
            except Exception as exc:
                return jsonify({"error": str(exc)}), 401
            if not user.is_active:
                return jsonify({"error": "User account is inactive"}), 403
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def require_admin(db_session) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                user = load_current_user(db_session)
            except Exception as exc:
                return jsonify({"error": str(exc)}), 401
            if not user.is_active:
                return jsonify({"error": "User account is inactive"}), 403
            if not user.is_admin:
                return jsonify({"error": "Admin access required"}), 403
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def verify_webhook(payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
    webhook = Webhook(Config.CLERK_WEBHOOK_SECRET)
    verified = webhook.verify(payload, headers)
    if isinstance(verified, bytes):
        verified = verified.decode("utf-8")
    return verified if isinstance(verified, dict) else {}

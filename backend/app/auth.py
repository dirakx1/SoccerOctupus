"""Auth and Clerk sync helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache, wraps
from typing import Any, Callable

import jwt
from flask import current_app, g, jsonify, request
from sqlalchemy.exc import IntegrityError
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
    primary_email_address = payload.get("primary_email_address")
    if isinstance(primary_email_address, dict) and primary_email_address.get("email_address"):
        return primary_email_address["email_address"]
    primary_email_address_id = payload.get("primary_email_address_id")
    for address in payload.get("email_addresses", []):
        if address.get("id") == primary_email_address_id:
            return address.get("email_address", "")
    if payload.get("email"):
        return payload["email"]
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


def _set_if_changed(user: User, field: str, value: Any) -> bool:
    if getattr(user, field) == value:
        return False
    setattr(user, field, value)
    return True


def _apply_identity(
    user: User,
    identity: ClerkIdentity,
    *,
    overwrite_missing: bool,
    sync_last_sign_in: bool = True,
) -> bool:
    changed = False

    if identity.email:
        changed = _set_if_changed(user, "email", identity.email) or changed

    if overwrite_missing or identity.first_name is not None:
        changed = _set_if_changed(user, "first_name", identity.first_name) or changed

    if overwrite_missing or identity.last_name is not None:
        changed = _set_if_changed(user, "last_name", identity.last_name) or changed

    if overwrite_missing or identity.avatar_url is not None:
        changed = _set_if_changed(user, "avatar_url", identity.avatar_url) or changed

    if sync_last_sign_in and identity.last_sign_in_at is not None:
        changed = _set_if_changed(user, "last_sign_in_at", identity.last_sign_in_at) or changed

    return changed


def _initial_email(identity: ClerkIdentity) -> str:
    return identity.email or f"{identity.clerk_user_id}@pending.clerk.local"


def sync_user(
    identity: ClerkIdentity,
    db_session,
    *,
    reactivate: bool = True,
    overwrite_missing: bool = True,
    sync_last_sign_in: bool = True,
) -> User:
    user = User.query.filter_by(clerk_user_id=identity.clerk_user_id).one_or_none()
    if user is None:
        user = User(
            clerk_user_id=identity.clerk_user_id,
            email=_initial_email(identity),
            first_name=None,
            last_name=None,
            avatar_url=None,
            is_admin=False,
            is_active=True,
            last_sign_in_at=identity.last_sign_in_at,
            deleted_at=None,
        )
        _apply_identity(user, identity, overwrite_missing=overwrite_missing, sync_last_sign_in=sync_last_sign_in)
        db_session.session.add(user)
        try:
            db_session.session.commit()
        except IntegrityError:
            db_session.session.rollback()
            user = User.query.filter_by(clerk_user_id=identity.clerk_user_id).one_or_none()
            if user is None:
                raise
            changed = _apply_identity(
                user,
                identity,
                overwrite_missing=overwrite_missing,
                sync_last_sign_in=sync_last_sign_in,
            )
            if reactivate:
                changed = _set_if_changed(user, "is_active", True) or changed
                changed = _set_if_changed(user, "deleted_at", None) or changed
            if changed:
                db_session.session.commit()
        return user

    changed = _apply_identity(
        user,
        identity,
        overwrite_missing=overwrite_missing,
        sync_last_sign_in=sync_last_sign_in,
    )
    if reactivate:
        changed = _set_if_changed(user, "is_active", True) or changed
        changed = _set_if_changed(user, "deleted_at", None) or changed
    if changed:
        db_session.session.commit()
    return user


def deactivate_user(clerk_user_id: str, db_session) -> None:
    user = User.query.filter_by(clerk_user_id=clerk_user_id).one_or_none()
    if user is None:
        return
    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)
    db_session.session.commit()


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url)


def _decode_token(token: str, key: Any) -> dict[str, Any]:
    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


def _local_jwks_key(token: str, jwks_json: str) -> Any:
    jwks = json.loads(jwks_json)
    keys = jwks.get("keys") if isinstance(jwks, dict) else None
    if keys is None:
        keys = [jwks]
    if not keys:
        raise ValueError("CLERK_JWKS_JSON has no keys")

    header = jwt.get_unverified_header(token)
    key_id = header.get("kid")
    selected_key = next((key for key in keys if key.get("kid") == key_id), None)
    if selected_key is None and len(keys) == 1:
        selected_key = keys[0]
    if selected_key is None:
        raise ValueError("No matching Clerk JWKS key")

    return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(selected_key))


def _local_public_key() -> str:
    return Config.CLERK_JWT_PUBLIC_KEY.strip().replace("\\n", "\n")


def verify_session_token(token: str) -> dict[str, Any]:
    local_public_key = _local_public_key()
    if local_public_key:
        return _decode_token(token, local_public_key)

    local_jwks_json = Config.CLERK_JWKS_JSON.strip()
    if local_jwks_json:
        return _decode_token(token, _local_jwks_key(token, local_jwks_json))

    signing_key = _jwks_client(Config.CLERK_JWKS_URL).get_signing_key_from_jwt(token)
    return _decode_token(token, signing_key.key)


def load_current_user(db_session) -> User:
    if hasattr(g, "current_user"):
        return g.current_user
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise PermissionError("Missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    claims = verify_session_token(token)
    identity = build_identity_from_claims(claims)
    user = sync_user(identity, db_session, overwrite_missing=False, sync_last_sign_in=False)
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

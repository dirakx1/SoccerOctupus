"""Cycle-based feature usage limits."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from flask import jsonify
from sqlalchemy.exc import IntegrityError

from .billing import PAID_STATUSES, PAID_TIERS
from .db.models import (
    FeatureLimitPolicy,
    User,
    UserFeatureCycleLimit,
    UserFeatureLimitOverride,
    utcnow,
)

FEATURE_MATCH_PREDICTION = "match_prediction"
FEATURE_TOURNAMENT_SIMULATION = "tournament_simulation"
FEATURE_MATCH_MARKET = "match_market"
FEATURE_TOURNAMENT_MARKET = "tournament_market"

FEATURE_LABELS = {
    FEATURE_MATCH_PREDICTION: "Match predictions",
    FEATURE_TOURNAMENT_SIMULATION: "Tournament simulations",
    FEATURE_MATCH_MARKET: "Match markets",
    FEATURE_TOURNAMENT_MARKET: "Tournament markets",
}
FEATURE_KEYS = set(FEATURE_LABELS)
ORDERED_FEATURE_KEYS = [
    FEATURE_MATCH_PREDICTION,
    FEATURE_TOURNAMENT_SIMULATION,
    FEATURE_MATCH_MARKET,
    FEATURE_TOURNAMENT_MARKET,
]

TIERS = {"free", "basic", "pro"}
ORDERED_TIERS = ["free", "basic", "pro"]
DEFAULT_POLICIES = {
    ("free", FEATURE_MATCH_PREDICTION): 1,
    ("free", FEATURE_TOURNAMENT_SIMULATION): 1,
    ("free", FEATURE_MATCH_MARKET): 3,
    ("free", FEATURE_TOURNAMENT_MARKET): 3,
    ("basic", FEATURE_MATCH_PREDICTION): None,
    ("basic", FEATURE_TOURNAMENT_SIMULATION): None,
    ("basic", FEATURE_MATCH_MARKET): None,
    ("basic", FEATURE_TOURNAMENT_MARKET): None,
    ("pro", FEATURE_MATCH_PREDICTION): None,
    ("pro", FEATURE_TOURNAMENT_SIMULATION): None,
    ("pro", FEATURE_MATCH_MARKET): None,
    ("pro", FEATURE_TOURNAMENT_MARKET): None,
}


@dataclass(frozen=True)
class UsageReservation:
    allowed: bool
    cycle_limit_id: int | None
    response: Any = None


def _session(db_session):
    return getattr(db_session, "session", db_session)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _now(now: datetime | None = None) -> datetime:
    return _aware(now) or utcnow()


def _add_month(value: datetime) -> datetime:
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _normalize_limit(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        as_int = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit_count must be null or a non-negative integer") from exc
    if as_int < 0:
        raise ValueError("limit_count must be null or a non-negative integer")
    return as_int


def validate_tier(tier: str) -> str:
    if tier not in TIERS:
        raise ValueError("Unknown tier")
    return tier


def validate_feature_key(feature_key: str) -> str:
    if feature_key not in FEATURE_KEYS:
        raise ValueError("Unknown feature")
    return feature_key


def ensure_default_feature_limit_policies(db_session) -> None:
    session = _session(db_session)
    existing = {
        (row.tier, row.feature_key)
        for row in FeatureLimitPolicy.query.filter(
            FeatureLimitPolicy.tier.in_(ORDERED_TIERS),
            FeatureLimitPolicy.feature_key.in_(ORDERED_FEATURE_KEYS),
        )
    }
    for (tier, feature_key), limit_count in DEFAULT_POLICIES.items():
        if (tier, feature_key) not in existing:
            session.add(FeatureLimitPolicy(tier=tier, feature_key=feature_key, limit_count=limit_count))
    session.commit()


def effective_usage_tier(user: User, now: datetime | None = None) -> str:
    current = _now(now)
    if user.is_admin:
        return "pro"
    tier = user.subscription_tier or "free"
    period_end = _aware(user.subscription_current_period_end)
    if tier in PAID_TIERS and user.subscription_status in PAID_STATUSES and (period_end is None or current < period_end):
        return tier
    return "free"


def _ensure_anchor(user: User, db_session, now: datetime) -> datetime:
    anchor = _aware(user.usage_cycle_anchor_at) or _aware(user.created_at) or now
    if user.usage_cycle_anchor_at is None:
        user.usage_cycle_anchor_at = anchor
        session = _session(db_session)
        session.add(user)
        session.commit()
    return anchor


def current_usage_cycle(user: User, db_session, now: datetime | None = None) -> tuple[datetime, datetime, str]:
    current = _now(now)
    tier = effective_usage_tier(user, current)
    period_start = _aware(user.subscription_current_period_start)
    period_end = _aware(user.subscription_current_period_end)
    if tier in PAID_TIERS and period_start and period_end and period_start <= current < period_end:
        return period_start, period_end, tier

    anchor = _ensure_anchor(user, db_session, current)
    cycle_start = anchor
    cycle_end = _add_month(cycle_start)
    while current >= cycle_end:
        cycle_start = cycle_end
        cycle_end = _add_month(cycle_start)
    while current < cycle_start:
        cycle_end = cycle_start
        cycle_start = _add_month(cycle_start.replace(year=cycle_start.year - 1)) if cycle_start.month == 12 else cycle_start.replace(month=cycle_start.month - 1)
    return cycle_start, cycle_end, tier


def _active_override(user: User, feature_key: str, now: datetime) -> UserFeatureLimitOverride | None:
    return (
        UserFeatureLimitOverride.query.filter_by(user_id=user.id, feature_key=feature_key, is_active=True)
        .filter(UserFeatureLimitOverride.starts_at <= now)
        .filter((UserFeatureLimitOverride.ends_at.is_(None)) | (UserFeatureLimitOverride.ends_at > now))
        .order_by(UserFeatureLimitOverride.created_at.desc(), UserFeatureLimitOverride.id.desc())
        .first()
    )


def _limit_values(user: User, feature_key: str, tier: str, now: datetime) -> tuple[int | None, str, str | None]:
    override = _active_override(user, feature_key, now)
    if override:
        return override.limit_count, "user_override", override.note
    policy = FeatureLimitPolicy.query.filter_by(tier=tier, feature_key=feature_key).one()
    return policy.limit_count, "policy", None


def ensure_cycle_limits(user: User, db_session, now: datetime | None = None) -> list[UserFeatureCycleLimit]:
    session = _session(db_session)
    current = _now(now)
    cycle_start, cycle_end, tier = current_usage_cycle(user, db_session, current)
    ensure_default_feature_limit_policies(db_session)

    rows = {
        row.feature_key: row
        for row in UserFeatureCycleLimit.query.filter_by(user_id=user.id, cycle_start=cycle_start, cycle_end=cycle_end)
    }
    changed = False
    for feature_key in ORDERED_FEATURE_KEYS:
        limit_count, limit_source, override_note = _limit_values(user, feature_key, tier, current)
        if feature_key in rows:
            row = rows[feature_key]
            if row.tier != tier and row.limit_source != "manual_cycle_override":
                row.tier = tier
                row.limit_count = limit_count
                row.used_count = 0
                row.limit_source = limit_source
                row.override_note = override_note
                row.overridden_by_user_id = None
                session.add(row)
                changed = True
            continue
        row = UserFeatureCycleLimit(
            user_id=user.id,
            tier=tier,
            feature_key=feature_key,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
            limit_count=limit_count,
            used_count=0,
            limit_source=limit_source,
            override_note=override_note,
        )
        session.add(row)
        rows[feature_key] = row
        changed = True
    if changed:
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return ensure_cycle_limits(user, db_session, current)
    return [rows[key] for key in ORDERED_FEATURE_KEYS]


def _serialize_row(row: UserFeatureCycleLimit) -> dict[str, Any]:
    unlimited = row.limit_count is None
    remaining = None if unlimited else max((row.limit_count or 0) - row.used_count, 0)
    return {
        "feature_key": row.feature_key,
        "label": FEATURE_LABELS[row.feature_key],
        "limit_count": row.limit_count,
        "used_count": row.used_count,
        "remaining_count": remaining,
        "unlimited": unlimited,
        "limit_source": row.limit_source,
    }


def serialize_usage(user: User, db_session, now: datetime | None = None) -> dict[str, Any]:
    rows = ensure_cycle_limits(user, db_session, now)
    cycle_start, cycle_end, tier = current_usage_cycle(user, db_session, now)
    return {
        "tier": tier,
        "cycle_start": cycle_start.isoformat(),
        "cycle_end": cycle_end.isoformat(),
        "features": [_serialize_row(row) for row in rows],
    }


def feature_limit_response(row: UserFeatureCycleLimit):
    return jsonify(
        {
            "error": f"{FEATURE_LABELS[row.feature_key]} limit reached",
            "code": "feature_limit_reached",
            "feature_key": row.feature_key,
            "limit_count": row.limit_count,
            "used_count": row.used_count,
            "remaining_count": 0,
            "cycle_start": row.cycle_start.isoformat(),
            "cycle_end": row.cycle_end.isoformat(),
            "plans_url": "/pricing",
        }
    ), 402


def reserve_feature_usage(
    user: User,
    feature_key: str,
    db_session,
    now: datetime | None = None,
    *,
    commit: bool = True,
) -> UsageReservation:
    validate_feature_key(feature_key)
    session = _session(db_session)
    ensure_cycle_limits(user, db_session, now)
    cycle_start, cycle_end, _tier = current_usage_cycle(user, db_session, now)
    query = UserFeatureCycleLimit.query.filter_by(
        user_id=user.id,
        feature_key=feature_key,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
    )
    row = query.with_for_update().one()
    if row.limit_count is None:
        return UsageReservation(True, None)
    if row.used_count >= row.limit_count:
        return UsageReservation(False, row.id, feature_limit_response(row))
    row.used_count += 1
    session.add(row)
    if commit:
        session.commit()
    return UsageReservation(True, row.id)


def release_feature_usage(cycle_limit_id: int | None, db_session) -> None:
    if cycle_limit_id is None:
        return
    session = _session(db_session)
    row = session.get(UserFeatureCycleLimit, cycle_limit_id)
    if row is None:
        return
    row.used_count = max(row.used_count - 1, 0)
    session.add(row)
    session.commit()


def serialize_policies(db_session) -> dict[str, Any]:
    ensure_default_feature_limit_policies(db_session)
    policies = FeatureLimitPolicy.query.order_by(FeatureLimitPolicy.tier, FeatureLimitPolicy.feature_key).all()
    by_tier: dict[str, dict[str, Any]] = {tier: {} for tier in ORDERED_TIERS}
    for policy in policies:
        by_tier.setdefault(policy.tier, {})[policy.feature_key] = policy.limit_count
    return {
        "features": [{"feature_key": key, "label": FEATURE_LABELS[key]} for key in ORDERED_FEATURE_KEYS],
        "tiers": by_tier,
    }


def update_policies(payload: dict[str, Any], db_session) -> dict[str, Any]:
    policies = payload.get("policies")
    if not isinstance(policies, list):
        raise ValueError("policies must be a list")
    ensure_default_feature_limit_policies(db_session)
    session = _session(db_session)
    for item in policies:
        if not isinstance(item, dict):
            raise ValueError("policy entries must be objects")
        tier = validate_tier(item.get("tier"))
        feature_key = validate_feature_key(item.get("feature_key"))
        limit_count = _normalize_limit(item.get("limit_count"))
        policy = FeatureLimitPolicy.query.filter_by(tier=tier, feature_key=feature_key).one_or_none()
        if policy is None:
            policy = FeatureLimitPolicy(tier=tier, feature_key=feature_key)
        policy.limit_count = limit_count
        session.add(policy)
    session.commit()
    return serialize_policies(db_session)


def serialize_user_limits(user: User, db_session, now: datetime | None = None) -> dict[str, Any]:
    usage = serialize_usage(user, db_session, now)
    current = _now(now)
    overrides = (
        UserFeatureLimitOverride.query.filter_by(user_id=user.id, is_active=True)
        .filter(UserFeatureLimitOverride.starts_at <= current)
        .filter((UserFeatureLimitOverride.ends_at.is_(None)) | (UserFeatureLimitOverride.ends_at > current))
        .order_by(UserFeatureLimitOverride.feature_key)
        .all()
    )
    usage["overrides"] = [
        {
            "id": override.id,
            "feature_key": override.feature_key,
            "limit_count": override.limit_count,
            "starts_at": override.starts_at.isoformat(),
            "ends_at": override.ends_at.isoformat() if override.ends_at else None,
            "note": override.note,
        }
        for override in overrides
    ]
    return usage


def upsert_user_override(user: User, payload: dict[str, Any], admin: User, db_session) -> dict[str, Any]:
    feature_key = validate_feature_key(payload.get("feature_key"))
    limit_count = _normalize_limit(payload.get("limit_count"))
    starts_at_value = payload.get("starts_at")
    if isinstance(starts_at_value, str) and starts_at_value:
        starts_at_value = datetime.fromisoformat(starts_at_value)
    starts_at = _aware(starts_at_value) if isinstance(starts_at_value, datetime) else None
    if starts_at is None:
        starts_at = utcnow()
    ends_at = payload.get("ends_at")
    if isinstance(ends_at, str) and ends_at:
        ends_at = datetime.fromisoformat(ends_at)
    ends_at = _aware(ends_at) if isinstance(ends_at, datetime) else None
    note = payload.get("note") if isinstance(payload.get("note"), str) else None

    session = _session(db_session)
    existing = UserFeatureLimitOverride.query.filter_by(user_id=user.id, feature_key=feature_key, is_active=True).all()
    for override in existing:
        override.is_active = False
        session.add(override)
    override = UserFeatureLimitOverride(
        user_id=user.id,
        feature_key=feature_key,
        limit_count=limit_count,
        starts_at=starts_at,
        ends_at=ends_at,
        is_active=True,
        created_by_user_id=admin.id,
        note=note,
    )
    session.add(override)
    session.commit()
    return serialize_user_limits(user, db_session)


def override_current_cycle_limit(user: User, feature_key: str, payload: dict[str, Any], admin: User, db_session) -> dict[str, Any]:
    feature_key = validate_feature_key(feature_key)
    limit_count = _normalize_limit(payload.get("limit_count"))
    note = payload.get("note") if isinstance(payload.get("note"), str) else None
    session = _session(db_session)
    ensure_cycle_limits(user, db_session)
    cycle_start, cycle_end, _tier = current_usage_cycle(user, db_session)
    row = UserFeatureCycleLimit.query.filter_by(
        user_id=user.id,
        feature_key=feature_key,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
    ).one()
    row.limit_count = limit_count
    row.limit_source = "manual_cycle_override"
    row.override_note = note
    row.overridden_by_user_id = admin.id
    session.add(row)
    session.commit()
    return serialize_user_limits(user, db_session)

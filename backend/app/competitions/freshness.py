from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_

from ..db.base import db
from ..db.models import (
    CompetitionEdition,
    CompetitionEditionRefresh,
    Fixture,
    StandingsSnapshot,
)
from .config import CompetitionEditionConfig
from .sync import sync_season


KICKOFF_WINDOW = timedelta(hours=2)
REFRESH_LEASE = timedelta(minutes=2)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def freshness_limits(
    config: CompetitionEditionConfig, fixtures: list[Fixture], now: datetime
) -> tuple[str, int, int]:
    now = _utc(now)
    if any(fixture.status == "in_progress" for fixture in fixtures):
        return "live", config.live_refresh_seconds, config.live_stale_seconds
    if any(abs((_utc(fixture.kickoff_at) - now).total_seconds()) <= KICKOFF_WINDOW.total_seconds() for fixture in fixtures):
        return "kickoff_window", config.kickoff_window_refresh_seconds, config.kickoff_window_stale_seconds
    if config.current_from <= now.date() <= config.current_until:
        return "in_season", config.in_season_refresh_seconds, config.in_season_stale_seconds
    return "off_season", config.off_season_refresh_seconds, config.in_season_stale_seconds


def serialize_freshness(
    state: CompetitionEditionRefresh, config: CompetitionEditionConfig, fixtures: list[Fixture], now: datetime
) -> dict:
    now = _utc(now)
    source_updated_at = _utc(state.source_updated_at)
    window, ttl_seconds, stale_seconds = freshness_limits(config, fixtures, now)
    age_seconds = max(0, (now - source_updated_at).total_seconds())
    refreshing = bool(state.refresh_lease_until and _utc(state.refresh_lease_until) > now)
    if age_seconds >= stale_seconds:
        status = "hard_stale"
    elif refreshing:
        status = "refreshing"
    elif state.last_error and age_seconds > ttl_seconds:
        status = "stale"
    else:
        status = "fresh"
    return {
        "status": status,
        "window": window,
        "source": "ESPN",
        "source_updated_at": source_updated_at.isoformat(),
        "refresh_failed": bool(state.last_error),
        "retryable": status in {"stale", "hard_stale"},
    }


def refresh_on_demand(
    config: CompetitionEditionConfig, edition: CompetitionEdition, *, now: datetime | None = None
) -> dict:
    now = _utc(now or datetime.now(timezone.utc))
    fixtures = Fixture.query.filter_by(competition_edition_id=edition.id).all()
    state = CompetitionEditionRefresh.query.filter_by(competition_edition_id=edition.id).one_or_none()
    if state is None:
        snapshot = StandingsSnapshot.query.filter_by(
            competition_edition_id=edition.id
        ).order_by(StandingsSnapshot.source_updated_at.desc()).first()
        fixture_updates = [fixture.source_updated_at for fixture in fixtures]
        source_updates = ([snapshot.source_updated_at] if snapshot else []) + fixture_updates
        if not source_updates:
            return {
                "status": "hard_stale",
                "window": freshness_limits(config, fixtures, now)[0],
                "source": "ESPN",
                "source_updated_at": None,
                "refresh_failed": False,
                "retryable": True,
            }
        source_updated_at = min(_utc(value) for value in source_updates)
        state = CompetitionEditionRefresh(
            competition_edition_id=edition.id,
            source_updated_at=source_updated_at,
            last_attempt_at=source_updated_at,
        )
        db.session.add(state)
        db.session.commit()
    _, ttl_seconds, _ = freshness_limits(config, fixtures, now)
    if (now - _utc(state.source_updated_at)).total_seconds() <= ttl_seconds:
        return serialize_freshness(state, config, fixtures, now)

    acquired = CompetitionEditionRefresh.query.filter(
        CompetitionEditionRefresh.id == state.id,
        or_(
            CompetitionEditionRefresh.refresh_lease_until.is_(None),
            CompetitionEditionRefresh.refresh_lease_until <= now,
        ),
    ).update(
        {
            CompetitionEditionRefresh.last_attempt_at: now,
            CompetitionEditionRefresh.refresh_started_at: now,
            CompetitionEditionRefresh.refresh_lease_until: now + REFRESH_LEASE,
        },
        synchronize_session=False,
    )
    db.session.commit()
    if acquired:
        try:
            sync_season(config, refresh_state_id=state.id, include_history=False)
        except Exception as exc:
            db.session.rollback()
            failed = db.session.get(CompetitionEditionRefresh, state.id)
            failed.last_attempt_at = now
            failed.last_error = str(exc)
            failed.refresh_started_at = None
            failed.refresh_lease_until = None
            db.session.commit()
    db.session.expire_all()
    state = db.session.get(CompetitionEditionRefresh, state.id)
    fixtures = Fixture.query.filter_by(competition_edition_id=edition.id).all()
    return serialize_freshness(state, config, fixtures, now)

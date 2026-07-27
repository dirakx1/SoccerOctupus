from __future__ import annotations

import hashlib
import json
from datetime import timezone

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ..db.models import ClubMatch, Fixture, MatchPredictionVersion
from .forecasting import MODEL_VERSION, build_club_baseline, poisson_forecast


def _team_history(team_id: int, as_of) -> tuple[list[dict], list[tuple]]:
    rows = ClubMatch.query.filter(
        ClubMatch.played_at < as_of,
        or_(ClubMatch.home_team_id == team_id, ClubMatch.away_team_id == team_id),
    ).order_by(ClubMatch.played_at.desc()).limit(30).all()
    matches = [
        {
            "played_at": row.played_at,
            "goals_for": row.home_score if row.home_team_id == team_id else row.away_score,
            "goals_against": row.away_score if row.home_team_id == team_id else row.home_score,
        }
        for row in rows
    ]
    sources = [
        ("history", row.id, row.home_score, row.away_score, row.source_updated_at)
        for row in rows
    ]
    current = Fixture.query.filter(
        Fixture.status == "completed",
        Fixture.kickoff_at < as_of,
        or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id),
    ).order_by(Fixture.kickoff_at.desc()).limit(30).all()
    for row in current:
        matches.append({
            "played_at": row.kickoff_at,
            "goals_for": row.home_score if row.home_team_id == team_id else row.away_score,
            "goals_against": row.away_score if row.home_team_id == team_id else row.home_score,
        })
        sources.append(("fixture", row.id, row.home_score, row.away_score, row.source_updated_at))
    return matches, sources


def get_or_create_prediction(fixture, config, db_session) -> MatchPredictionVersion:
    home_matches, home_rows = _team_history(fixture.home_team_id, fixture.kickoff_at)
    away_matches, away_rows = _team_history(fixture.away_team_id, fixture.kickoff_at)
    home = build_club_baseline(
        home_matches, promoted=fixture.home_team.slug in config.promoted_team_ids, as_of=fixture.kickoff_at
    )
    away = build_club_baseline(
        away_matches, promoted=fixture.away_team.slug in config.promoted_team_ids, as_of=fixture.kickoff_at
    )
    source_rows = sorted(set(home_rows + away_rows))
    source_updated_at = max(row[4] for row in source_rows)
    fingerprint_input = {
        "model": MODEL_VERSION,
        "fixture": fixture.id,
        "kickoff_at": fixture.kickoff_at.isoformat(),
        "teams": [fixture.home_team.slug, fixture.away_team.slug],
        "configuration_revision": config.configuration_revision,
        "promoted_teams": sorted(config.promoted_team_ids),
        "history": [(*row[:4], row[4].isoformat()) for row in source_rows],
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_input, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    existing = MatchPredictionVersion.query.filter_by(
        fixture_id=fixture.id, fingerprint=fingerprint
    ).one_or_none()
    if existing:
        return existing
    home_xg = max(0.2, min(4.0, 1.12 * home["attack"] / max(away["defence"], 0.35)))
    away_xg = max(0.2, min(4.0, away["attack"] / max(home["defence"], 0.35)))
    forecast = poisson_forecast(home_xg=home_xg, away_xg=away_xg)
    forecast.update({
        "baseline": {"home": home, "away": away},
        "confidence": round(min(len(home_matches), len(away_matches)) / 30, 3),
        "agents": {
            "available": ["statistical", "form"],
            "unavailable": [
                {"agent": "tactical", "reason": "No genuine club tactical input"},
                {"agent": "live_data", "reason": "No genuine club live-data input"},
                {"agent": "market_signals", "reason": "No genuine club market input"},
                {"agent": "squad_quality", "reason": "No genuine club squad input"},
                {"agent": "video", "reason": "No genuine club video input"},
            ],
        },
    })
    version = MatchPredictionVersion(
        fixture_id=fixture.id,
        fingerprint=fingerprint,
        model_version=MODEL_VERSION,
        source="ESPN club match history",
        source_updated_at=source_updated_at,
        forecast=forecast,
    )
    db_session.session.add(version)
    try:
        db_session.session.commit()
    except IntegrityError:
        db_session.session.rollback()
        return MatchPredictionVersion.query.filter_by(
            fixture_id=fixture.id, fingerprint=fingerprint
        ).one()
    return version


def serialize_prediction(version: MatchPredictionVersion) -> dict:
    source_updated_at = version.source_updated_at
    if source_updated_at.tzinfo is None:
        source_updated_at = source_updated_at.replace(tzinfo=timezone.utc)
    return {
        "version_id": version.id,
        "fixture_id": version.fixture_id,
        "home_team": version.fixture.home_team.display_name,
        "away_team": version.fixture.away_team.display_name,
        "model_version": version.model_version,
        "source": version.source,
        "source_updated_at": source_updated_at.isoformat(),
        "generated_at": version.created_at.isoformat(),
        **version.forecast,
    }

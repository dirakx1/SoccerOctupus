from datetime import datetime, timezone

from flask import Blueprint

from ..auth import require_user
from ..competitions import get_competition, get_edition, list_competitions
from ..db.base import db
from ..db.models import CompetitionEdition, StandingsSnapshot


bp = Blueprint("competitions", __name__, url_prefix="/api/competitions")


def _edition_response(edition):
    return {
        "competition": {
            "slug": edition.competition_slug,
            "display_name": edition.competition_display_name,
        },
        "edition": edition.public_dict(),
    }


@bp.get("")
def catalog():
    return {
        "competitions": [
            {
                "slug": edition.competition_slug,
                "display_name": edition.competition_display_name,
                "current_edition": edition.public_dict(),
            }
            for edition in list_competitions()
        ]
    }


@bp.get("/<competition_slug>")
def current_competition(competition_slug: str):
    edition = get_competition(competition_slug)
    return _edition_response(edition) if edition else ({"error": "Competition not found"}, 404)


@bp.get("/<competition_slug>/editions/<edition_slug>")
def competition_edition(competition_slug: str, edition_slug: str):
    edition = get_edition(competition_slug, edition_slug)
    return _edition_response(edition) if edition else ({"error": "Competition Edition not found"}, 404)


def _table_response(competition_slug: str, edition_slug: str, *, preview: bool = False):
    config = get_edition(competition_slug, edition_slug)
    if config is None:
        return {"error": "Competition Edition not found"}, 404
    edition = CompetitionEdition.query.filter_by(
        competition_slug=competition_slug, edition_slug=edition_slug
    ).one_or_none()
    if edition is None:
        return {"error": "League Table data is not available"}, 503
    snapshot = StandingsSnapshot.query.filter_by(
        competition_edition_id=edition.id
    ).order_by(StandingsSnapshot.source_updated_at.desc(), StandingsSnapshot.id.desc()).first()
    if snapshot is None:
        return {"error": "League Table data is not available"}, 503

    source_updated_at = snapshot.source_updated_at
    if source_updated_at.tzinfo is None:
        source_updated_at = source_updated_at.replace(tzinfo=timezone.utc)
    rows = snapshot.standings[:5] if preview else snapshot.standings
    standings = []
    for row in rows:
        item = {
            "position": row.position,
            "team": {
                "slug": row.team.slug,
                "display_name": row.team.display_name,
                "abbreviation": row.team.abbreviation,
            },
            "played": row.played,
            "goal_difference": row.goal_difference,
            "points": row.points,
        }
        if not preview:
            item.update({
                "won": row.won,
                "drawn": row.drawn,
                "lost": row.lost,
                "goals_for": row.goals_for,
                "goals_against": row.goals_against,
            })
        standings.append(item)
    return {
        "competition": {"slug": competition_slug},
        "edition": {"slug": edition_slug, "display_name": edition.display_name},
        "source": snapshot.source,
        "source_updated_at": source_updated_at.isoformat(),
        "stale": (datetime.now(timezone.utc) - source_updated_at).total_seconds()
        > config.in_season_stale_seconds,
        "standings": standings,
    }


@bp.get("/<competition_slug>/editions/<edition_slug>/table/preview")
def table_preview(competition_slug: str, edition_slug: str):
    return _table_response(competition_slug, edition_slug, preview=True)


@bp.get("/<competition_slug>/editions/<edition_slug>/table")
@require_user(db)
def league_table(competition_slug: str, edition_slug: str):
    return _table_response(competition_slug, edition_slug)

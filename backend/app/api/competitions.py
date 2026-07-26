from datetime import datetime, timezone

from flask import Blueprint, request

from ..auth import require_user
from ..competitions import get_competition, get_edition, list_competitions
from ..db.base import db
from ..db.models import CompetitionEdition, CompetitionEditionTeam, Fixture, StandingsSnapshot


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


def _fixture_item(fixture: Fixture):
    kickoff_at = fixture.kickoff_at
    source_updated_at = fixture.source_updated_at
    if kickoff_at.tzinfo is None:
        kickoff_at = kickoff_at.replace(tzinfo=timezone.utc)
    if source_updated_at.tzinfo is None:
        source_updated_at = source_updated_at.replace(tzinfo=timezone.utc)
    return {
        "id": fixture.id,
        "matchweek": fixture.matchweek,
        "kickoff_at": kickoff_at.isoformat(),
        "venue": fixture.venue,
        "status": fixture.status,
        "home_team": {
            "slug": fixture.home_team.slug,
            "display_name": fixture.home_team.display_name,
            "abbreviation": fixture.home_team.abbreviation,
            "score": fixture.home_score,
        },
        "away_team": {
            "slug": fixture.away_team.slug,
            "display_name": fixture.away_team.display_name,
            "abbreviation": fixture.away_team.abbreviation,
            "score": fixture.away_score,
        },
        "source_updated_at": source_updated_at.isoformat(),
    }


def _persisted_edition(competition_slug: str, edition_slug: str):
    config = get_edition(competition_slug, edition_slug)
    if config is None:
        return None, ({"error": "Competition Edition not found"}, 404)
    edition = CompetitionEdition.query.filter_by(
        competition_slug=competition_slug, edition_slug=edition_slug
    ).one_or_none()
    if edition is None:
        return None, ({"error": "Fixture data is not available"}, 503)
    return edition, None


@bp.get("/<competition_slug>/editions/<edition_slug>/fixtures/preview")
def fixture_preview(competition_slug: str, edition_slug: str):
    edition, error = _persisted_edition(competition_slug, edition_slug)
    if error:
        return error
    fixtures = Fixture.query.filter_by(competition_edition_id=edition.id)
    upcoming = fixtures.filter(Fixture.status.notin_(("completed", "cancelled", "abandoned"))).order_by(Fixture.kickoff_at).limit(3).all()
    results = fixtures.filter_by(status="completed").order_by(Fixture.kickoff_at.desc()).limit(3).all()
    return {
        "upcoming": [_fixture_item(fixture) for fixture in upcoming],
        "results": [_fixture_item(fixture) for fixture in results],
    }


@bp.get("/<competition_slug>/editions/<edition_slug>/fixtures")
@require_user(db)
def fixtures(competition_slug: str, edition_slug: str):
    mode = request.args.get("mode", "upcoming")
    if mode not in {"upcoming", "results"}:
        return {"error": "Invalid Fixture mode"}, 400
    matchweek_value = request.args.get("matchweek")
    try:
        requested_matchweek = int(matchweek_value) if matchweek_value else None
    except ValueError:
        return {"error": "Invalid Matchweek"}, 400

    edition, error = _persisted_edition(competition_slug, edition_slug)
    if error:
        return error
    all_fixtures = Fixture.query.filter_by(competition_edition_id=edition.id)
    if all_fixtures.count() == 0:
        return {"error": "Fixture data is not available"}, 503

    memberships = CompetitionEditionTeam.query.filter_by(competition_edition_id=edition.id).all()
    teams = sorted(
        (membership.team for membership in memberships),
        key=lambda team: team.display_name,
    )
    team_slug = request.args.get("team")
    selected_team = next((team for team in teams if team.slug == team_slug), None)
    if team_slug and selected_team is None:
        return {"error": "Team not found in Competition Edition"}, 400

    matchweeks = [
        row[0]
        for row in all_fixtures.with_entities(Fixture.matchweek)
        .filter(Fixture.matchweek.is_not(None))
        .distinct()
        .order_by(Fixture.matchweek)
    ]
    query = all_fixtures.filter(
        Fixture.status.in_(("completed", "cancelled", "abandoned"))
        if mode == "results"
        else Fixture.status.notin_(("completed", "cancelled", "abandoned"))
    )
    selected_matchweek = requested_matchweek
    if selected_matchweek is None:
        if mode == "upcoming":
            live = query.filter_by(status="in_progress").order_by(Fixture.matchweek).first()
            next_fixture = query.order_by(Fixture.kickoff_at).first()
            selected_matchweek = (live or next_fixture).matchweek if (live or next_fixture) else None
        else:
            latest_result = query.order_by(Fixture.kickoff_at.desc()).first()
            selected_matchweek = latest_result.matchweek if latest_result else None
    if selected_matchweek is not None:
        query = query.filter_by(matchweek=selected_matchweek)
    if selected_team is not None:
        query = query.filter(
            (Fixture.home_team_id == selected_team.id) | (Fixture.away_team_id == selected_team.id)
        )

    ordering = Fixture.kickoff_at.desc() if mode == "results" else Fixture.kickoff_at
    return {
        "edition": {"slug": edition_slug, "display_name": edition.display_name},
        "filters": {"mode": mode, "matchweek": selected_matchweek, "team": team_slug},
        "selected_matchweek": selected_matchweek,
        "matchweeks": matchweeks,
        "teams": [
            {"slug": team.slug, "display_name": team.display_name, "abbreviation": team.abbreviation}
            for team in teams
        ],
        "fixtures": [_fixture_item(fixture) for fixture in query.order_by(ordering).all()],
    }

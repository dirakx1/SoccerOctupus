from __future__ import annotations

import hashlib
import json

from ..db.base import db
from ..db.models import (
    ClubMatch,
    CompetitionEdition,
    CompetitionEditionRefresh,
    CompetitionEditionTeam,
    Fixture,
    FixtureProviderMapping,
    Standing,
    StandingsSnapshot,
    Team,
    TeamProviderMapping,
)
from .config import CompetitionEditionConfig
from .providers import EspnFixturesProvider, EspnStandingsProvider, ProviderDataError


def _sync_historical_matches(config: CompetitionEditionConfig) -> None:
    for source in config.historical_match_sources:
        data = EspnFixturesProvider().fetch(
            source.competition_id,
            source.edition,
            source.date_from.strftime("%Y%m%d"),
            source.date_until.strftime("%Y%m%d"),
        )
        for row in data.entries:
            if row.status != "completed" or row.home_score is None or row.away_score is None:
                continue
            teams = []
            for provider_team_id in (row.home_provider_team_id, row.away_provider_team_id):
                mapping = TeamProviderMapping.query.filter_by(
                    provider="espn", provider_team_id=provider_team_id
                ).one_or_none()
                if mapping is None:
                    team = Team(
                        slug=f"espn-{provider_team_id}",
                        display_name=f"ESPN Team {provider_team_id}",
                    )
                    db.session.add(team)
                    db.session.flush()
                    mapping = TeamProviderMapping(
                        provider="espn", provider_team_id=provider_team_id, team=team
                    )
                    db.session.add(mapping)
                teams.append(mapping.team)
            match = ClubMatch.query.filter_by(
                source="ESPN", provider_match_id=row.provider_fixture_id
            ).one_or_none()
            if match is None:
                match = ClubMatch(
                    source="ESPN",
                    provider_match_id=row.provider_fixture_id,
                    home_team=teams[0],
                    away_team=teams[1],
                )
                db.session.add(match)
            elif match.home_team_id != teams[0].id or match.away_team_id != teams[1].id:
                raise ProviderDataError(
                    f"ESPN historical Fixture {row.provider_fixture_id} has conflicting identity"
                )
            match.source_competition = source.competition_id
            match.source_edition = source.edition
            match.played_at = row.kickoff_at
            match.home_score = row.home_score
            match.away_score = row.away_score
            match.source_updated_at = data.fetched_at


def sync_season(
    config: CompetitionEditionConfig,
    *,
    refresh_state_id: int | None = None,
    include_history: bool = True,
) -> tuple[int, int, int]:
    mappings = dict(config.provider_team_mappings)
    if len(mappings) != len(config.provider_team_mappings):
        raise ProviderDataError("Edition configuration contains duplicate Team mappings")
    missing = set(config.participating_team_ids) - mappings.keys()
    if missing:
        raise ProviderDataError(f"Missing ESPN Team mappings: {', '.join(sorted(missing))}")
    if len(set(mappings.values())) != len(mappings):
        raise ProviderDataError("Edition configuration contains duplicate ESPN Team mappings")
    for team_slug, provider_id in mappings.items():
        persisted = TeamProviderMapping.query.filter_by(
            provider="espn", provider_team_id=provider_id
        ).one_or_none()
        if persisted is not None and persisted.team.slug != team_slug:
            raise ProviderDataError(
                f"ESPN Team {provider_id} is already mapped to {persisted.team.slug}"
            )

    provider_data = EspnStandingsProvider().fetch(
        config.provider_competition_id, config.provider_season
    )
    fixture_data = EspnFixturesProvider().fetch(
        config.provider_competition_id,
        config.provider_season,
        config.fixture_date_from.strftime("%Y%m%d"),
        config.fixture_date_until.strftime("%Y%m%d"),
    )
    reverse_mappings = {provider_id: team_slug for team_slug, provider_id in mappings.items()}
    for entry in provider_data.entries:
        if entry.provider_team_id not in reverse_mappings:
            raise ProviderDataError(
                f"Unknown ESPN Team mapping: {entry.provider_team_id} ({entry.team_name})"
            )
    missing_provider_teams = set(mappings.values()) - {
        entry.provider_team_id for entry in provider_data.entries
    }
    if missing_provider_teams:
        missing_slugs = sorted(reverse_mappings[team_id] for team_id in missing_provider_teams)
        raise ProviderDataError(f"Missing ESPN standings Teams: {', '.join(missing_slugs)}")
    for fixture in fixture_data.entries:
        unknown = {
            fixture.home_provider_team_id, fixture.away_provider_team_id
        } - reverse_mappings.keys()
        if unknown:
            raise ProviderDataError(f"Unknown ESPN Fixture Team mapping: {', '.join(sorted(unknown))}")
        if not config.fixture_date_from <= fixture.kickoff_at.date() <= config.fixture_date_until:
            raise ProviderDataError(
                f"ESPN Fixture {fixture.provider_fixture_id} is outside configured date bounds"
            )

    edition = CompetitionEdition.query.filter_by(
        competition_slug=config.competition_slug, edition_slug=config.edition_slug
    ).one_or_none()
    if edition is None:
        edition = CompetitionEdition(
            competition_slug=config.competition_slug,
            edition_slug=config.edition_slug,
            display_name=config.edition_display_name,
            configuration_revision=config.configuration_revision,
        )
        db.session.add(edition)
        db.session.flush()
    else:
        edition.display_name = config.edition_display_name
        edition.configuration_revision = config.configuration_revision

    teams = {}
    names = {reverse_mappings[row.provider_team_id]: row for row in provider_data.entries}
    for slug in config.participating_team_ids:
        team = Team.query.filter_by(slug=slug).one_or_none()
        provider_team = names.get(slug)
        if team is None:
            team = Team(slug=slug, display_name=slug.replace("-", " ").title())
            db.session.add(team)
            db.session.flush()
        if provider_team:
            team.display_name = provider_team.team_name
            team.abbreviation = provider_team.abbreviation
        teams[slug] = team

        if CompetitionEditionTeam.query.filter_by(
            competition_edition_id=edition.id, team_id=team.id
        ).one_or_none() is None:
            db.session.add(CompetitionEditionTeam(competition_edition_id=edition.id, team_id=team.id))
        mapping = TeamProviderMapping.query.filter_by(provider="espn", team_id=team.id).one_or_none()
        if mapping is None:
            db.session.add(TeamProviderMapping(
                provider="espn", provider_team_id=mappings[slug], team_id=team.id
            ))
        else:
            mapping.provider_team_id = mappings[slug]

    normalized = [
        {
            "team_slug": reverse_mappings[row.provider_team_id],
            "position": row.position,
            "played": row.played,
            "won": row.won,
            "drawn": row.drawn,
            "lost": row.lost,
            "goals_for": row.goals_for,
            "goals_against": row.goals_against,
            "goal_difference": row.goal_difference,
            "points": row.points,
        }
        for row in sorted(provider_data.entries, key=lambda item: item.position)
    ]
    content_hash = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    snapshot = StandingsSnapshot.query.filter_by(
        competition_edition_id=edition.id, content_hash=content_hash
    ).one_or_none()
    if snapshot is None:
        snapshot = StandingsSnapshot(
            competition_edition_id=edition.id,
            source="ESPN",
            source_updated_at=provider_data.fetched_at,
            content_hash=content_hash,
        )
        db.session.add(snapshot)
        for row in normalized:
            snapshot.standings.append(Standing(team=teams[row.pop("team_slug")], **row))
    else:
        snapshot.source_updated_at = provider_data.fetched_at

    for row in fixture_data.entries:
        mapping = FixtureProviderMapping.query.filter_by(
            provider="espn", provider_fixture_id=row.provider_fixture_id
        ).one_or_none()
        home_team = teams[reverse_mappings[row.home_provider_team_id]]
        away_team = teams[reverse_mappings[row.away_provider_team_id]]
        if mapping is None:
            fixture = Fixture.query.filter_by(
                competition_edition_id=edition.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
            ).one_or_none()
            if fixture is None:
                fixture = Fixture(
                    competition_edition_id=edition.id,
                    home_team=home_team,
                    away_team=away_team,
                    matchweek=row.matchweek,
                    kickoff_at=row.kickoff_at,
                    venue=row.venue,
                    status=row.status,
                    provider_status=row.provider_status,
                    home_score=row.home_score,
                    away_score=row.away_score,
                    source_updated_at=fixture_data.fetched_at,
                )
                db.session.add(fixture)
                db.session.flush()
            mapping = FixtureProviderMapping.query.filter_by(
                provider="espn", fixture_id=fixture.id
            ).one_or_none()
            if mapping is None:
                db.session.add(FixtureProviderMapping(
                    provider="espn", provider_fixture_id=row.provider_fixture_id, fixture=fixture
                ))
            else:
                mapping.provider_fixture_id = row.provider_fixture_id
        else:
            fixture = mapping.fixture
            if (
                fixture.competition_edition_id != edition.id
                or fixture.home_team_id != home_team.id
                or fixture.away_team_id != away_team.id
            ):
                raise ProviderDataError(
                    f"ESPN Fixture {row.provider_fixture_id} has conflicting identity"
                )
        fixture.kickoff_at = row.kickoff_at
        fixture.venue = row.venue
        fixture.status = row.status
        fixture.provider_status = row.provider_status
        fixture.home_score = row.home_score
        fixture.away_score = row.away_score
        fixture.source_updated_at = fixture_data.fetched_at

    source_updated_at = min(provider_data.fetched_at, fixture_data.fetched_at)
    refresh_state = (
        db.session.get(CompetitionEditionRefresh, refresh_state_id)
        if refresh_state_id is not None
        else CompetitionEditionRefresh.query.filter_by(competition_edition_id=edition.id).one_or_none()
    )
    if refresh_state is None:
        refresh_state = CompetitionEditionRefresh(
            competition_edition_id=edition.id,
            source_updated_at=source_updated_at,
            last_attempt_at=source_updated_at,
        )
        db.session.add(refresh_state)
    else:
        refresh_state.source_updated_at = source_updated_at
        refresh_state.last_attempt_at = source_updated_at
        refresh_state.last_error = None
        refresh_state.refresh_started_at = None
        refresh_state.refresh_lease_until = None

    if include_history:
        _sync_historical_matches(config)
    db.session.commit()
    return len(teams), len(normalized), len(fixture_data.entries)

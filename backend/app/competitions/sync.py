from __future__ import annotations

import hashlib
import json

from ..db.base import db
from ..db.models import (
    CompetitionEdition,
    CompetitionEditionTeam,
    Standing,
    StandingsSnapshot,
    Team,
    TeamProviderMapping,
)
from .config import CompetitionEditionConfig
from .providers import EspnStandingsProvider, ProviderDataError


def sync_season(config: CompetitionEditionConfig) -> tuple[int, int]:
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

    db.session.commit()
    return len(teams), len(normalized)

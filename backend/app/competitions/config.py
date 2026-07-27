from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class HistoricalMatchSource:
    competition_id: str
    edition: str
    date_from: date
    date_until: date


@dataclass(frozen=True)
class CompetitionEditionConfig:
    competition_slug: str
    competition_display_name: str
    competition_display_name_key: str
    edition_slug: str
    edition_display_name: str
    edition_display_name_key: str
    configuration_revision: str
    format: str
    capabilities: tuple[str, ...]
    current_from: date
    current_until: date
    fixture_date_from: date
    fixture_date_until: date
    points_for_win: int
    points_for_draw: int
    table_tiebreakers: tuple[str, ...]
    outcome_bands: tuple[tuple[str, int, int], ...]
    participating_team_ids: tuple[str, ...]
    provider_competition_id: str
    provider_season: str
    provider_team_mappings: tuple[tuple[str, str], ...]
    live_refresh_seconds: int
    kickoff_window_refresh_seconds: int
    in_season_refresh_seconds: int
    off_season_refresh_seconds: int
    live_stale_seconds: int
    kickoff_window_stale_seconds: int
    in_season_stale_seconds: int
    historical_match_sources: tuple[HistoricalMatchSource, ...] = ()
    promoted_team_ids: tuple[str, ...] = ()

    def public_dict(self) -> dict:
        return {
            "slug": self.edition_slug,
            "display_name": self.edition_display_name,
            "format": self.format,
            "capabilities": list(self.capabilities),
            "current_from": self.current_from.isoformat(),
            "current_until": self.current_until.isoformat(),
        }

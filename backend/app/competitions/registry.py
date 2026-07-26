from __future__ import annotations

from datetime import date

from .config import CompetitionEditionConfig
from .editions import PREMIER_LEAGUE_2026_27


_EDITIONS = (PREMIER_LEAGUE_2026_27,)


def get_edition(
    competition_slug: str, edition_slug: str
) -> CompetitionEditionConfig | None:
    return next(
        (
            edition
            for edition in _EDITIONS
            if edition.competition_slug == competition_slug
            and edition.edition_slug == edition_slug
        ),
        None,
    )


def get_competition(
    competition_slug: str, as_of: date | None = None
) -> CompetitionEditionConfig | None:
    as_of = as_of or date.today()
    prepared_editions = [
        edition
        for edition in _EDITIONS
        if edition.competition_slug == competition_slug
        and edition.current_from <= as_of
    ]
    return max(prepared_editions, key=lambda edition: edition.current_from, default=None)


def list_competitions() -> tuple[CompetitionEditionConfig, ...]:
    return tuple(
        edition
        for competition_slug in dict.fromkeys(edition.competition_slug for edition in _EDITIONS)
        if (edition := get_competition(competition_slug)) is not None
    )

import click

from ..db.base import db
from .providers import ProviderDataError
from .registry import get_edition
from .sync import sync_season


@click.command("sync-season")
@click.argument("competition_slug")
@click.argument("edition_slug")
def sync_season_command(competition_slug: str, edition_slug: str) -> None:
    config = get_edition(competition_slug, edition_slug)
    if config is None:
        raise click.ClickException("Competition Edition not found")
    try:
        team_count, standing_count = sync_season(config)
    except Exception as exc:
        db.session.rollback()
        if isinstance(exc, ProviderDataError):
            raise click.ClickException(str(exc)) from exc
        raise
    click.echo(f"Synced {team_count} Teams and {standing_count} standings")

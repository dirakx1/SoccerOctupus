"""Flask commands for preparing, refreshing, and activating league seasons."""

from __future__ import annotations

import json
import click
from flask import Flask
from datetime import datetime, timedelta, timezone

from ..config import Config
from ..db.base import db
from .espn import EspnDataError
from .evidence import collect_league_evidence
from .fotmob import FotMobHistoricalAuditor, admission_report
from .forecast import sync_forecast_ledger
from .prediction import LeaguePredictionModel
from .season import SeasonManager, SeasonSpec, season_spec
from .store import LeagueSeasonStore, SeasonDataError
from .zep import LeagueZepGraphManager
from ..runtime_settings import RuntimeSettingsService


def register_cli(app: Flask) -> None:
    @app.cli.command("league-season")
    @click.option("--competition", default="premier-league", show_default=True)
    @click.option("--season", "season_name", default="2026-27", show_default=True)
    @click.option("--provider-competition")
    @click.option("--provider-season", type=int)
    @click.option("--starts-on", help="Season start date (YYYY-MM-DD).")
    @click.option("--ends-on", help="Season end date (YYYY-MM-DD).")
    @click.option("--display-name")
    @click.option(
        "--history",
        "history_entries",
        multiple=True,
        help="Historical source as competition:season:providerCompetition:providerSeason:startsOn:endsOn.",
    )
    @click.option("--action", type=click.Choice(("prepare", "refresh", "activate")), multiple=True)
    @click.option("--fetch", is_flag=True, help="Fetch the ESPN snapshot during prepare.")
    def league_season(
        competition: str,
        season_name: str,
        provider_competition: str | None,
        provider_season: int | None,
        starts_on: str | None,
        ends_on: str | None,
        display_name: str | None,
        history_entries: tuple[str, ...],
        action: tuple[str, ...],
        fetch: bool,
    ) -> None:
        """Manage one edition (actions run in the order supplied)."""
        try:
            custom = any(value is not None for value in (provider_competition, provider_season, starts_on, ends_on, display_name)) or bool(history_entries)
            if custom:
                if not all(value is not None for value in (provider_competition, provider_season, starts_on, ends_on, display_name)):
                    raise click.ClickException("custom seasons require provider competition/season, dates, and display name")
                history = tuple(_parse_history_entry(entry) for entry in history_entries)
                spec = SeasonSpec(
                    competition=competition,
                    season=season_name,
                    provider_competition=provider_competition,
                    provider_season=provider_season,
                    starts_on=starts_on,
                    ends_on=ends_on,
                    display_name=display_name,
                    history=history,
                )
            else:
                spec = season_spec(competition, season_name)
            manager = SeasonManager(Config.DATA_DIR + "/leagues")
            actions = action or ("prepare",)
            for selected in actions:
                if selected == "prepare":
                    manager.prepare(spec, fetch=fetch)
                elif selected == "refresh":
                    manager.refresh(spec)
                else:
                    manager.activate(spec)
            click.echo(f"Managed {competition}/{season_name}: {', '.join(actions)}")
        except (EspnDataError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

    @app.cli.command("league-refresh-active")
    @click.option("--competition", help="Refresh the active season for one competition.")
    @click.option("--force", is_flag=True, help="Refresh even when the snapshot is fresh and no match is near kickoff.")
    @click.option("--now", "now_value", help="UTC ISO timestamp for deterministic operator testing.")
    def league_refresh_active(competition: str | None, force: bool, now_value: str | None) -> None:
        """Refresh only the active league season around matchday windows."""
        try:
            store = LeagueSeasonStore(Config.DATA_DIR + "/leagues")
            active = next((
                item for item in store.catalog()
                if item.get("active") and (competition is None or item.get("competition") == competition)
            ), None)
            if not active:
                suffix = f" for {competition}" if competition else ""
                raise click.ClickException(f"no active league season{suffix}")
            data = store.load(active["competition"], active["season"])
            edition = data.edition
            provider = edition.get("provider")
            if not isinstance(provider, dict) or provider.get("name") != "espn":
                raise ValueError("active league edition has invalid ESPN provider metadata")
            required = ("competition", "season")
            if any(not str(provider.get(key, "")).strip() for key in required):
                raise ValueError("active league edition is missing ESPN provider competition or season")
            try:
                provider_season = int(provider["season"])
            except (TypeError, ValueError) as exc:
                raise ValueError("active league edition has an invalid ESPN provider season") from exc
            if isinstance(provider["season"], bool) or not all(
                isinstance(edition.get(key), str) and edition[key].strip()
                for key in ("competition", "season", "displayName", "startsOn", "endsOn")
            ):
                raise ValueError("active league edition is missing required refresh metadata")
            history = edition.get("history", ())
            promoted = edition.get("promotedTeamIds", ())
            if not isinstance(history, (list, tuple)) or any(not isinstance(item, dict) for item in history):
                raise ValueError("active league edition has invalid history metadata")
            if not isinstance(promoted, (list, tuple)) or any(not isinstance(item, (str, int)) for item in promoted):
                raise ValueError("active league edition has invalid promoted-team metadata")
            spec = SeasonSpec(
                competition=edition["competition"],
                season=edition["season"],
                provider_competition=str(provider["competition"]).strip(),
                provider_season=provider_season,
                starts_on=edition["startsOn"],
                ends_on=edition["endsOn"],
                display_name=edition["displayName"],
                promoted_team_ids=tuple(str(item) for item in promoted),
                history=tuple(history),
            )
            now = _parse_refresh_datetime(now_value, strict=True) or datetime.now(timezone.utc)
            snapshot_path = data.directory / "snapshot.json"
            raw_snapshot = {}
            before_fetched_at = "missing"
            if snapshot_path.exists():
                try:
                    parsed_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
                    if isinstance(parsed_snapshot, dict):
                        raw_snapshot = parsed_snapshot
                        before_fetched_at = str(raw_snapshot.get("fetchedAt") or "missing")
                    else:
                        before_fetched_at = "invalid"
                except (OSError, json.JSONDecodeError):
                    before_fetched_at = "invalid"
            reasons: list[str] = []
            if force:
                reasons.append("forced")
            else:
                in_match_window = False
                for fixture in data.fixtures:
                    if str(fixture.get("status", "")).lower() in {"cancelled", "postponed"}:
                        continue
                    try:
                        kickoff = datetime.fromisoformat(str(fixture["kickoff"]).replace("Z", "+00:00"))
                    except (KeyError, TypeError, ValueError):
                        continue
                    if kickoff.tzinfo is None:
                        kickoff = kickoff.replace(tzinfo=timezone.utc)
                    if kickoff - timedelta(minutes=30) <= now <= kickoff + timedelta(hours=3):
                        in_match_window = True
                        break
                if in_match_window:
                    reasons.append("match-window")
                fetched_at = _parse_refresh_datetime(raw_snapshot.get("fetchedAt"))
                if fetched_at is None or now - fetched_at > timedelta(hours=6):
                    reasons.append("snapshot-stale")
            if not reasons:
                click.echo(
                    f"Skipped {active['competition']}/{active['season']}: "
                    f"reason=outside-match-window-and-snapshot-fresh beforeFetchedAt={before_fetched_at} "
                    f"fixtures={len(data.fixtures)} standings={len(data.standings)}"
                )
                return
            refreshed_path = SeasonManager(Config.DATA_DIR + "/leagues").refresh(spec, include_history=False)
            refreshed = store.load(active["competition"], active["season"])
            refreshed_snapshot = json.loads((refreshed_path / "snapshot.json").read_text(encoding="utf-8"))
            ledger = sync_forecast_ledger(
                refreshed,
                now=now,
                settings=RuntimeSettingsService.current(db),
            )
            click.echo(
                f"Refreshed {active['competition']}/{active['season']}: reason={','.join(reasons)} "
                f"beforeFetchedAt={before_fetched_at} afterFetchedAt={refreshed_snapshot.get('fetchedAt', 'missing')} "
                f"fixtures={len(refreshed.fixtures)} standings={len(refreshed.standings)} "
                f"forecasts={len(ledger.get('forecasts', []))}"
            )
        except click.ClickException:
            raise
        except Exception as exc:
            raise click.ClickException(f"active league refresh failed: {exc}") from exc

    @app.cli.command("probe-espn")
    @click.option("--competition", default="eng.1", show_default=True)
    @click.option("--season", "season_name", default=2026, show_default=True, type=int)
    def probe_espn(competition: str, season_name: int) -> None:
        """Probe ESPN and report normalized fixture/standing counts."""
        manager = SeasonManager(Config.DATA_DIR + "/leagues")
        spec = season_spec("premier-league", "2026-27")
        try:
            snapshot = manager.client.snapshot(
                competition=competition,
                season=season_name,
                starts_on=spec.starts_on,
                ends_on=spec.ends_on,
            )
        except Exception as exc:
            raise click.ClickException(f"ESPN probe failed: {exc}") from exc
        click.echo(f"ESPN {competition}/{season_name}: {len(snapshot['fixtures'])} fixtures, {len(snapshot['standings'])} standings")

    @app.cli.command("probe-league-providers")
    @click.option("--competition", default="premier-league", show_default=True)
    @click.option("--season", "season_name", default="2026-27", show_default=True)
    @click.option("--home", help="Club name; defaults to the first scheduled fixture.")
    @click.option("--away", help="Club name; defaults to the first scheduled fixture.")
    def probe_league_providers(competition: str, season_name: str, home: str | None, away: str | None) -> None:
        """Probe league provider capability without printing keys or raw payloads."""
        try:
            data = LeagueSeasonStore(Config.DATA_DIR + "/leagues").load(competition, season_name)
        except SeasonDataError as exc:
            raise click.ClickException(str(exc)) from exc
        scheduled = next((item for item in data.fixtures if item.get("status") == "scheduled"), None)
        teams = {str(team["id"]): team["name"] for team in data.teams}
        if not home or not away:
            if not scheduled:
                raise click.ClickException("no scheduled fixture available; pass --home and --away")
            home = home or teams[str(scheduled["homeTeamId"])]
            away = away or teams[str(scheduled["awayTeamId"])]
        kickoff = datetime.fromisoformat(str((scheduled or {}).get("kickoff", datetime.now(timezone.utc).isoformat())).replace("Z", "+00:00"))
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        with app.app_context():
            evidence = collect_league_evidence(
                home=home,
                away=away,
                kickoff=kickoff,
                competition=competition,
                season=season_name,
                graph_id=str(data.edition.get("leagueGraph", {}).get("graphId", "")),
                settings=RuntimeSettingsService.current(db),
            )
        click.echo(f"{competition} provider probe: {home} vs {away}")
        for row in evidence:
            summary = ", ".join(sorted(row.get("evidence", {}).keys())) or "none"
            click.echo(f"{row['provider']}: {row['status']} | {row['reason']} | evidence fields: {summary}")

    @app.cli.command("league-backtest")
    @click.option("--competition", default="premier-league", show_default=True)
    @click.option("--season", "season_name", default="2024-25", show_default=True)
    def league_backtest(competition: str, season_name: str) -> None:
        """Report a leakage-safe ESPN-only walk-forward baseline."""
        try:
            data = LeagueSeasonStore(Config.DATA_DIR + "/leagues").load(competition, season_name)
        except SeasonDataError as exc:
            raise click.ClickException(str(exc)) from exc
        model = LeaguePredictionModel(teams=data.teams, completed_fixtures=data.completed_fixtures, promoted_team_ids=data.promoted_team_ids)
        rows = []
        for fixture in data.fixtures:
            if fixture.get("status") != "completed":
                continue
            kickoff = datetime.fromisoformat(str(fixture["kickoff"]).replace("Z", "+00:00"))
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)
            forecast = model.predict(fixture["homeTeamId"], fixture["awayTeamId"], kickoff=kickoff)
            actual = "home" if fixture["homeScore"] > fixture["awayScore"] else "away" if fixture["homeScore"] < fixture["awayScore"] else "draw"
            probability = max(1e-12, forecast["probabilities"][actual])
            rows.append((probability, forecast["probabilities"], actual))
        if not rows:
            raise click.ClickException("season has no completed fixtures")
        log_loss = -sum(__import__("math").log(probability) for probability, _, _ in rows) / len(rows)
        brier = sum(sum((probabilities[key] - (key == actual)) ** 2 for key in ("home", "draw", "away")) for _, probabilities, actual in rows) / len(rows)
        click.echo(f"ESPN walk-forward {competition}/{season_name}: matches={len(rows)} logLoss={log_loss:.4f} brier={brier:.4f} adjustmentsApplied=false")

    @app.cli.command("league-fotmob-backfill")
    @click.option("--season", "season_names", multiple=True, default=("2024-25", "2025-26"), show_default=True)
    @click.option("--refresh", is_flag=True, help="Discard the normalized cache and refetch match details.")
    def league_fotmob_backfill(season_names: tuple[str, ...], refresh: bool) -> None:
        """Reconcile historical EPL FotMob fixtures and cache compact stats."""
        store = LeagueSeasonStore(Config.DATA_DIR + "/leagues")
        auditor = FotMobHistoricalAuditor()
        for season_name in season_names:
            try:
                data = store.load("premier-league", season_name)
                result = auditor.run(data, refresh=refresh)
            except (SeasonDataError, OSError, TypeError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc
            click.echo(
                f"FotMob {season_name}: fixtures={result['fixtureCount']} reconciled={result['reconciledCount']} "
                f"quarantined={result['quarantinedCount']} stats={result['statsCoverage']} "
                f"xg={result['xgCoverage']} shots={result['shotsCoverage']}"
            )

    @app.cli.command("league-fotmob-admission")
    @click.option("--season", "season_names", multiple=True, default=("2024-25", "2025-26"), show_default=True)
    def league_fotmob_admission(season_names: tuple[str, ...]) -> None:
        """Report the leakage-safe FotMob numerical admission gate."""
        store = LeagueSeasonStore(Config.DATA_DIR + "/leagues")
        try:
            seasons = {season_name: store.load("premier-league", season_name) for season_name in season_names}
            report = admission_report(seasons)
            report_path = Config.DATA_DIR + "/leagues/fotmob-admission-report.json"
            from pathlib import Path
            Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except (SeasonDataError, OSError, TypeError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(json.dumps(report, indent=2, sort_keys=True))

    @app.cli.command("league-zep-graph")
    @click.option("--competition", default="premier-league", show_default=True)
    @click.option("--season", "season_name", default="2026-27", show_default=True)
    @click.option("--create", is_flag=True, help="Create/update the edition-scoped remote graph.")
    @click.option("--resume-existing", is_flag=True, help="Populate an existing empty edition graph after verification.")
    def league_zep_graph(competition: str, season_name: str, create: bool, resume_existing: bool) -> None:
        """Prepare or explicitly build the Zep graph for one league edition."""
        try:
            data = LeagueSeasonStore(Config.DATA_DIR + "/leagues").load(competition, season_name)
        except SeasonDataError as exc:
            raise click.ClickException(str(exc)) from exc
        manager = LeagueZepGraphManager()
        graph_id = manager.graph_id(data)
        episode_count = len(manager.episodes(data))
        if create and resume_existing:
            raise click.ClickException("choose either --create or --resume-existing")
        if not create:
            if resume_existing:
                create = True
            else:
                click.echo(f"Ready {competition}/{season_name}: graphId={graph_id} episodes={episode_count}; not built (pass --create)")
                return
        if not resume_existing and str(data.edition.get("leagueGraph", {}).get("graphId", "")) == graph_id:
            click.echo(f"Already built {competition}/{season_name}: graphId={graph_id}; no episodes added")
            return
        with app.app_context():
            settings = RuntimeSettingsService.current(db)
            if not settings.zep_api_key:
                raise click.ClickException("Zep API key is not configured")
            try:
                built_id = manager.resume_existing(data, api_key=settings.zep_api_key) if resume_existing else manager.build(data, api_key=settings.zep_api_key)
            except ValueError as exc:
                raise click.ClickException(str(exc)) from exc
        edition = dict(data.edition)
        edition["leagueGraph"] = manager.metadata(built_id)
        SeasonManager._write(data.directory / "edition.json", edition)
        click.echo(f"{'Resumed' if resume_existing else 'Built'} {competition}/{season_name}: graphId={built_id} episodes={episode_count}")


def _parse_refresh_datetime(value: str | datetime | None, *, strict: bool = False) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            if strict:
                raise click.ClickException("--now must be an ISO timestamp") from exc
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _parse_history_entry(value: str) -> dict[str, str | int]:
    parts = value.split(":")
    if len(parts) != 6:
        raise click.ClickException("--history requires competition:season:providerCompetition:providerSeason:startsOn:endsOn")
    competition, season, provider_competition, provider_season, starts_on, ends_on = parts
    return {
        "competition": competition,
        "season": season,
        "providerCompetition": provider_competition,
        "providerSeason": int(provider_season),
        "startsOn": starts_on,
        "endsOn": ends_on,
        "file": f"history-{competition}-{season}.json",
    }

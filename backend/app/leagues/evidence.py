"""League-only provider evidence adapters.

ESPN remains the numerical source of truth.  These adapters are deliberately
separate from the World Cup collectors: a provider can contribute context to
a league prediction only when its response is real, identifiable, and available
before the requested kickoff.  No adapter has a synthetic fallback.
"""

from __future__ import annotations

import concurrent.futures
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

import requests

from ..config import Config
from ..runtime_settings import RuntimeSettings

ADMITTED = "admitted"
UNAVAILABLE = "unavailable"
EXCLUDED = "excluded"
ERROR = "error"
_STATUSES = {ADMITTED, UNAVAILABLE, EXCLUDED, ERROR}
LEAGUE_PROVIDERS = {
    "premier-league": {"name": "Premier League", "sofascore": 17, "fotmob": 47, "fotmobName": "Premier League", "country": "ENG", "scores365": 7, "opta": "eng.1"},
    "la-liga": {"name": "La Liga", "sofascore": 8, "fotmob": 87, "fotmobName": "LaLiga", "country": "ESP", "scores365": 11, "opta": "esp.1"},
    "bundesliga": {"name": "Bundesliga", "sofascore": 35, "fotmob": 54, "fotmobName": "Bundesliga", "country": "GER", "scores365": 25, "opta": "ger.1"},
}
CLUB_NAME_ALIASES = {
    "1 fc koln": "fc cologne",
    "fc koln": "fc cologne",
    "deportivo alaves": "alaves",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _name(value: Any) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()
    return CLUB_NAME_ALIASES.get(normalized, normalized)


def _team_matches(value: Any, expected: str) -> bool:
    actual, target = _name(value), _name(expected)
    return bool(actual and target and (actual == target or actual.endswith(target) or target.endswith(actual)))


@dataclass(frozen=True)
class ProviderEvidence:
    provider: str
    status: str
    source: str
    fetched_at: str
    reason: str
    evidence: dict[str, Any]

    def __post_init__(self):
        if self.status not in _STATUSES:
            raise ValueError(f"unknown provider evidence status: {self.status}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "source": self.source,
            "fetchedAt": self.fetched_at,
            "reason": self.reason,
            "evidence": self.evidence,
        }


def _unavailable(provider: str, reason: str, source: str | None = None) -> ProviderEvidence:
    return ProviderEvidence(provider, UNAVAILABLE, source or provider, _now(), reason, {})


def _excluded(provider: str, reason: str, source: str | None = None, evidence: dict[str, Any] | None = None) -> ProviderEvidence:
    return ProviderEvidence(provider, EXCLUDED, source or provider, _now(), reason, evidence or {})


class _Adapter:
    provider = "provider"

    def __init__(self, *, get: Callable[..., Any] = requests.get, timeout: float = 3):
        self.get = get
        self.timeout = timeout

    def _get_json(self, url: str, **kwargs: Any) -> tuple[Any | None, str | None]:
        try:
            response = self.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            payload = response.json()
            return payload, None
        except requests.RequestException as exc:
            return None, f"request failed: {exc.__class__.__name__}"
        except (TypeError, ValueError) as exc:
            return None, f"malformed response: {exc.__class__.__name__}"


class SofaScoreLeagueAdapter(_Adapter):
    provider = "SofaScore"
    base_url = Config.SOFASCORE_BASE_URL

    def __init__(self, *, tournament_id: int = 17, competition_name: str = "Premier League", **kwargs: Any):
        super().__init__(**kwargs)
        self.tournament_id = tournament_id
        self.competition_name = competition_name

    def collect(self, home: str, away: str, kickoff: datetime) -> ProviderEvidence:
        ids: dict[str, str] = {}
        for team in (home, away):
            payload, error = self._get_json(f"{self.base_url}/search/all", params={"q": team}, headers=Config.SOFASCORE_HEADERS)
            if error:
                return _unavailable(self.provider, error, f"{self.base_url}/search/all")
            matches = payload.get("results", []) if isinstance(payload, dict) else []
            row = next((item for item in matches if _team_matches(item.get("entity", {}).get("name"), team)), None)
            if not row:
                return _excluded(self.provider, f"no verified {self.competition_name} club identity for {team}", f"{self.base_url}/search/all")
            entity = row.get("entity", {})
            team_id = entity.get("id")
            if not team_id:
                return _excluded(self.provider, f"missing club ID for {team}", f"{self.base_url}/search/all")
            ids[team] = str(team_id)

        summaries: dict[str, dict[str, Any]] = {}
        for team, team_id in ids.items():
            payload, error = self._get_json(f"{self.base_url}/team/{team_id}/events/last/0", headers=Config.SOFASCORE_HEADERS)
            if error:
                return _unavailable(self.provider, error, f"{self.base_url}/team/{{id}}/events/last/0")
            events = payload.get("events", []) if isinstance(payload, dict) else []
            completed = []
            for event in events:
                event_time = datetime.fromtimestamp(event.get("startTimestamp", 0), timezone.utc) if event.get("startTimestamp") else None
                status = event.get("status", {})
                tournament = event.get("tournament", {})
                unique_tournament = tournament.get("uniqueTournament", {}) if isinstance(tournament, dict) else {}
                tournament_id = unique_tournament.get("id") or tournament.get("uniqueTournamentId")
                if str(tournament_id) != str(self.tournament_id):
                    continue
                if not event_time or event_time >= kickoff or status.get("type") != "finished":
                    continue
                home_score = event.get("homeScore", {}).get("current")
                away_score = event.get("awayScore", {}).get("current")
                if not isinstance(home_score, int) or not isinstance(away_score, int):
                    continue
                home_name = event.get("homeTeam", {}).get("name")
                away_name = event.get("awayTeam", {}).get("name")
                if not (_team_matches(home_name, team) or _team_matches(away_name, team)):
                    continue
                scored, conceded = (home_score, away_score) if _team_matches(home_name, team) else (away_score, home_score)
                completed.append({"scored": scored, "conceded": conceded, "kickoff": event_time.isoformat()})
            if not completed:
                return _excluded(self.provider, f"no verified pre-kickoff completed matches for {team}", f"{self.base_url}/team/{{id}}/events/last/0")
            summaries[team] = {
                "providerTeamId": team_id,
                "completedMatches": len(completed),
                "goalsForPerMatch": round(sum(item["scored"] for item in completed) / len(completed), 3),
                "goalsAgainstPerMatch": round(sum(item["conceded"] for item in completed) / len(completed), 3),
            }
        return ProviderEvidence(self.provider, ADMITTED, f"{self.base_url}/team/{{id}}/events/last/0", _now(), "verified pre-kickoff completed club matches", summaries)


class FotMobLeagueAdapter(_Adapter):
    provider = "FotMob"
    league_url = "https://www.fotmob.com/api/data/leagues"
    team_url = "https://www.fotmob.com/api/data/teams"
    match_url = "https://www.fotmob.com/api/data/matchDetails"
    headers = {
        "Accept": "application/json",
        "Referer": "https://www.fotmob.com/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    }

    def __init__(self, *, season: str = "2026/2027", competition_id: int = 47, competition_name: str = "Premier League", country: str = "ENG", **kwargs: Any):
        super().__init__(**kwargs)
        self.season = season
        self.competition_id = competition_id
        self.competition_name = competition_name
        self.country = country

    def collect(self, home: str, away: str, kickoff: datetime, *, season: str | None = None) -> ProviderEvidence:
        fetched_at = datetime.now(timezone.utc)
        if fetched_at >= kickoff:
            return _excluded(self.provider, "FotMob response would be fetched after kickoff", self.league_url)
        season = season or self.season
        payload, error = self._get_json(self.league_url, params={"id": self.competition_id, "season": season}, headers=self.headers)
        if error:
            return _unavailable(self.provider, error, self.league_url)
        details = payload.get("details", {}) if isinstance(payload, dict) else {}
        if details.get("id") != self.competition_id or details.get("name") != self.competition_name or details.get("selectedSeason") != season:
            return _excluded(self.provider, f"league response did not verify {self.competition_name} season", self.league_url)
        table = payload.get("table", []) if isinstance(payload, dict) else []
        rows = table[0].get("data", {}).get("table", {}).get("all", []) if table and isinstance(table[0], dict) else []
        if not isinstance(rows, list):
            return _excluded(self.provider, "league response table is malformed", self.league_url)
        verified_ids: dict[str, str] = {}
        for team in (home, away):
            row = next((item for item in rows if isinstance(item, dict) and _team_matches(item.get("name"), team)), None)
            if not row or not row.get("id") or not _team_matches(row.get("name"), team):
                return _excluded(self.provider, f"league table did not verify {team}", self.league_url)
            verified_ids[team] = str(row["id"])

        normalized_teams: dict[str, dict[str, Any]] = {}
        for team, team_id in verified_ids.items():
            detail, detail_error = self._get_json(self.team_url, params={"id": team_id, "ccode3": self.country}, headers=self.headers)
            if detail_error:
                return _unavailable(self.provider, detail_error, self.team_url)
            team_details = detail.get("details", {}) if isinstance(detail, dict) else {}
            if (
                str(team_details.get("id")) != team_id
                or not _team_matches(team_details.get("name"), team)
                or team_details.get("primaryLeagueId") != self.competition_id
            ):
                return _excluded(self.provider, f"team response did not verify {team} in {self.competition_name}", self.team_url)
            stat_rows = detail.get("stats", {}).get("teams", []) if isinstance(detail, dict) else []
            stats: dict[str, float] = {}
            for stat_row in stat_rows if isinstance(stat_rows, list) else []:
                participant = stat_row.get("participant", {}) if isinstance(stat_row, dict) else {}
                stat = participant.get("stat", {}) if isinstance(participant, dict) else {}
                stat_name = stat.get("name")
                if stat_name not in {"rating_team", "goals_team_match", "goals_conceded_team_match", "possession_percentage_team"}:
                    continue
                if not _team_matches(participant.get("name"), team) or str(participant.get("teamId")) != team_id:
                    continue
                try:
                    stats[stat_name] = float(stat["value"])
                except (KeyError, TypeError, ValueError):
                    continue
            if not stats:
                return _excluded(self.provider, f"team stats unavailable or malformed for {team}", self.team_url)
            normalized_teams[team] = {"providerTeamId": team_id, "stats": stats}
        evidence: dict[str, Any] = dict(normalized_teams)
        matches = payload.get("fixtures", {}).get("allMatches", []) if isinstance(payload, dict) else []
        fixture_candidates = []
        for item in matches if isinstance(matches, list) else []:
            event_time = _dt(item.get("status", {}).get("utcTime")) if isinstance(item, dict) else None
            if (
                item.get("id")
                and event_time
                and abs(event_time - kickoff) <= timedelta(minutes=15)
                and _team_matches(item.get("home", {}).get("name"), home)
                and _team_matches(item.get("away", {}).get("name"), away)
            ):
                fixture_candidates.append(item)
        if len(fixture_candidates) == 1:
            fixture_id = str(fixture_candidates[0]["id"])
            detail, detail_error = self._get_json(self.match_url, params={"matchId": fixture_id}, headers=self.headers)
            if not detail_error and isinstance(detail, dict):
                lineup = detail.get("content", {}).get("lineup", {})
                lineup_teams = [lineup.get("homeTeam"), lineup.get("awayTeam")] if isinstance(lineup, dict) else []
                normalized_lineups = []
                for expected_name, team_row in zip((home, away), lineup_teams):
                    if not isinstance(team_row, dict) or not _team_matches(team_row.get("name"), expected_name):
                        normalized_lineups = []
                        break
                    starters = team_row.get("starters", [])
                    if not isinstance(starters, list) or len(starters) != 11:
                        normalized_lineups = []
                        break
                    normalized_lineups.append({
                        "team": expected_name,
                        "formation": team_row.get("formation"),
                        "totalStarterMarketValue": team_row.get("totalStarterMarketValue"),
                        "starters": [{"id": str(player.get("id", "")), "name": player.get("name"), "positionId": player.get("usualPlayingPositionId"), "marketValue": player.get("marketValue")} for player in starters],
                        "unavailable": [{"id": str(player.get("id", "")), "name": player.get("name"), "type": player.get("unavailability", {}).get("type"), "expectedReturn": player.get("unavailability", {}).get("expectedReturn")} for player in team_row.get("unavailable", []) if isinstance(player, dict)],
                    })
                if len(normalized_lineups) == 2:
                    evidence["fixtureContext"] = {"providerFixtureId": fixture_id, "lineupConfirmed": True, "teams": normalized_lineups}
        return ProviderEvidence(self.provider, ADMITTED, f"{self.league_url}; {self.team_url}; {self.match_url}", fetched_at.isoformat(), f"verified {self.competition_name} table, club identity, current stats, and any confirmed pre-kickoff lineup", evidence)


class Scores365LeagueAdapter(_Adapter):
    provider = "365Scores"
    base_url = "https://webws.365scores.com/web/games/"
    headers = {
        "Accept": "application/json",
        "Origin": "https://www.365scores.com",
        "Referer": "https://www.365scores.com/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }

    def __init__(self, *, competition_id: int = 7, competition_name: str = "Premier League", **kwargs: Any):
        super().__init__(**kwargs)
        self.competition_id = competition_id
        self.competition_name = competition_name

    def collect(self, home: str, away: str, kickoff: datetime) -> ProviderEvidence:
        payload, error = self._get_json(
            self.base_url,
            params={
                "appTypeId": "5",
                "langId": "1",
                "timezoneName": "UTC",
                "sports": "1",
                "competitions": str(self.competition_id),
            },
            headers=self.headers,
        )
        if error:
            return _unavailable(self.provider, error, self.base_url)
        games = payload.get("games", []) if isinstance(payload, dict) else []
        candidates = []
        for game in games:
            if not isinstance(game, dict) or str(game.get("competitionId")) != str(self.competition_id):
                continue
            home_name = game.get("homeCompetitor", {}).get("name")
            away_name = game.get("awayCompetitor", {}).get("name")
            if not (_team_matches(home_name, home) and _team_matches(away_name, away)):
                continue
            event_time = _dt(game.get("startTime") or game.get("date") or game.get("startTimeUTC"))
            if (
                event_time
                and event_time > datetime.now(timezone.utc)
                and abs(event_time - kickoff) <= timedelta(minutes=15)
            ):
                candidates.append((event_time, game))
        if not candidates:
            return _excluded(self.provider, f"no verified pre-kickoff {self.competition_name} fixture with competitionId={self.competition_id}", self.base_url)
        event_time, game = candidates[0]
        odds = game.get("odds")
        if not isinstance(odds, dict):
            return _excluded(self.provider, f"verified {self.competition_name} fixture has no odds in current 365Scores payload", self.base_url)
        values = None
        for keys in (("homeOdds", "drawOdds", "awayOdds"), ("1", "X", "2")):
            try:
                candidate = [float(odds[key]) for key in keys]
            except (KeyError, TypeError, ValueError):
                continue
            if all(value > 1 for value in candidate):
                values = candidate
                break
        if values is None:
            return _excluded(self.provider, "fixture odds are malformed", self.base_url)
        home_odd, draw_odd, away_odd = values
        raw = [1 / home_odd, 1 / draw_odd, 1 / away_odd]
        total = sum(raw)
        return ProviderEvidence(self.provider, ADMITTED, self.base_url, _now(), f"verified pre-kickoff {self.competition_name} market odds", {"kickoff": event_time.isoformat(), "homeImplied": round(raw[0] / total, 4), "drawImplied": round(raw[1] / total, 4), "awayImplied": round(raw[2] / total, 4), "marketMargin": round(total - 1, 4)})


class YouTubeLeagueAdapter(_Adapter):
    provider = "YouTube"
    search_url = "https://www.googleapis.com/youtube/v3/search"
    aliases = {
        "AFC Bournemouth": "Bournemouth",
        "Brighton & Hove Albion": "Brighton",
        "Manchester United": "Manchester United",
        "Manchester City": "Manchester City",
        "Newcastle United": "Newcastle",
        "Nottingham Forest": "Nottingham Forest",
        "Tottenham Hotspur": "Tottenham",
    }
    blocked_terms = ("world cup", "fifa", "national team", "national squad", "international", "synthetic", "estimate")

    def __init__(self, api_key: str = "", *, competition_name: str = "Premier League", **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = (api_key or "").strip()
        self.competition_name = competition_name
        self._cache: dict[tuple[str, str], list[dict[str, Any]]] = {}

    def collect(self, home: str, away: str, kickoff: datetime) -> ProviderEvidence:
        if not self.api_key:
            return _unavailable(self.provider, "YouTube API key is not configured", self.search_url)
        collected: dict[str, list[dict[str, Any]]] = {}
        for team in (home, away):
            videos, error = self._search_team(team, kickoff)
            if error:
                return _unavailable(self.provider, error, self.search_url)
            if not videos:
                return _excluded(self.provider, f"no verified pre-kickoff {self.competition_name} videos for {team}", self.search_url)
            collected[team] = videos
        return ProviderEvidence(
            self.provider,
            ADMITTED,
            self.search_url,
            _now(),
            f"verified team-specific pre-kickoff {self.competition_name} video metadata",
            {"teams": {team: {"videoCount": len(videos), "videos": videos} for team, videos in collected.items()}},
        )

    def _search_team(self, team: str, kickoff: datetime) -> tuple[list[dict[str, Any]], str | None]:
        alias = self.aliases.get(team, team)
        key = (alias, kickoff.astimezone(timezone.utc).isoformat())
        if key in self._cache:
            return self._cache[key], None
        payload, error = self._get_json(
            self.search_url,
            params={
                "part": "snippet",
                "q": f"{alias} {self.competition_name} tactical analysis form highlights",
                "type": "video",
                "maxResults": 5,
                "publishedBefore": kickoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "relevanceLanguage": "en",
                "order": "relevance",
                "fields": "items(id/videoId,snippet(title,channelTitle,publishedAt))",
                "key": self.api_key,
            },
        )
        if error:
            return [], error
        items = payload.get("items", []) if isinstance(payload, dict) else []
        videos = []
        alias_name = _name(alias)
        for item in items if isinstance(items, list) else []:
            snippet = item.get("snippet", {}) if isinstance(item, dict) else {}
            video_id = item.get("id", {}).get("videoId") if isinstance(item, dict) else None
            published = _dt(snippet.get("publishedAt"))
            title = str(snippet.get("title", "")).strip()
            channel = str(snippet.get("channelTitle", "")).strip()
            searchable = _name(f"{title} {channel}")
            relevant = bool(alias_name and alias_name in searchable)
            blocked = any(term in searchable for term in self.blocked_terms)
            if video_id and title and channel and published and published < kickoff and relevant and not blocked:
                videos.append({"videoId": str(video_id), "title": title[:180], "channel": channel[:100], "publishedAt": published.isoformat()})
        self._cache[key] = videos
        return videos, None


class ZepLeagueAdapter(_Adapter):
    provider = "Zep"

    def __init__(self, api_key: str = "", graph_id: str = "", *, competition_name: str = "Premier League", **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key, self.graph_id = (api_key or "").strip(), (graph_id or "").strip()
        self.competition_name = competition_name

    def collect(self, home: str, away: str, kickoff: datetime) -> ProviderEvidence:
        if not self.api_key or not self.graph_id:
            reason = "edition-scoped league graph ID is not configured" if self.api_key else "Zep API key is not configured"
            return _unavailable(self.provider, reason, "https://api.getzep.com/api/v2")
        try:
            from zep_cloud.client import Zep
            client = Zep(api_key=self.api_key, timeout=self.timeout)
            results = client.graph.search(query=f"{self.competition_name} {home} {away}", graph_id=self.graph_id, limit=5)
            rows = getattr(results, "facts", None) or getattr(results, "edges", None) or []
            facts = []
            for row in rows[:5]:
                value = getattr(row, "fact", None) or getattr(row, "name", None)
                text = str(value or "")
                lowered = text.lower()
                valid_at = _dt(getattr(row, "valid_at", None) or getattr(row, "created_at", None))
                if (
                    text
                    and valid_at
                    and valid_at < kickoff
                    and (_name(home) in _name(text) or _name(away) in _name(text))
                    and not any(word in lowered for word in ("synthetic", "estimate", "national team", "world cup", "benchmark", "fallback"))
                ):
                    facts.append(text[:240])
            if not facts:
                return _excluded(self.provider, "configured graph returned no verifiable club facts", "https://api.getzep.com/api/v2")
            return ProviderEvidence(self.provider, ADMITTED, "https://api.getzep.com/api/v2", _now(), "configured graph returned club context", {"factCount": len(facts), "facts": facts})
        except ImportError:
            return _unavailable(self.provider, "zep-cloud dependency is not installed", "https://api.getzep.com/api/v2")
        except Exception as exc:
            return ProviderEvidence(self.provider, ERROR, "https://api.getzep.com/api/v2", _now(), f"Zep request failed: {exc.__class__.__name__}", {})


class OptaLeagueAdapter(_Adapter):
    provider = "Opta"

    def __init__(self, api_key: str = "", base_url: str = "", *, competition_code: str = "eng.1", competition_name: str = "Premier League", **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key, self.base_url = (api_key or "").strip(), (base_url or "").rstrip("/")
        self.competition_code = competition_code
        self.competition_name = competition_name

    def collect(self, home: str, away: str, kickoff: datetime) -> ProviderEvidence:
        if not self.api_key:
            return _unavailable(self.provider, "Opta API key is not configured", self.base_url or "Opta")
        if not self.base_url:
            return _unavailable(self.provider, "Opta base URL is not configured", "Opta")
        payload, error = self._get_json(f"{self.base_url}/squads", params={"_rt": "b", "_fmt": "json", "_ak": self.api_key, "comp": self.competition_code})
        if error:
            return _unavailable(self.provider, error, f"{self.base_url}/squads")
        squads = payload.get("squads", payload.get("squad", [])) if isinstance(payload, dict) else []
        names = [item.get("contestantName") or item.get("teamName") for item in squads if isinstance(item, dict)]
        if not any(_team_matches(value, home) for value in names) or not any(_team_matches(value, away) for value in names):
            return _excluded(self.provider, f"configured Opta response did not verify both {self.competition_name} clubs", f"{self.base_url}/squads")
        return ProviderEvidence(self.provider, ADMITTED, f"{self.base_url}/squads", _now(), f"verified {self.competition_name} club identities from configured Opta feed", {"verifiedTeams": [home, away]})


def collect_league_evidence(*, home: str, away: str, kickoff: datetime, settings: RuntimeSettings, competition: str = "premier-league", season: str = "2026-27", graph_id: str = "", get: Callable[..., Any] = requests.get) -> list[dict[str, Any]]:
    """Collect provider evidence concurrently; numerical use is separately gated."""
    # A request for a completed/past kickoff cannot safely use current live
    # provider context.  Return an explicit exclusion instead of leaking it
    # into a historical prediction or backtest.
    if kickoff <= datetime.now(timezone.utc):
        return [
            _excluded(provider, "requested kickoff has passed; live context is not leakage-safe", provider).as_dict()
            for provider in ("SofaScore", "FotMob", "365Scores", "YouTube", "Zep", "Opta")
        ]
    provider_config = LEAGUE_PROVIDERS.get(competition)
    if provider_config is None:
        return [
            _unavailable(provider, f"{provider} adapter is not yet verified for {competition}", provider).as_dict()
            for provider in ("SofaScore", "FotMob", "365Scores", "YouTube", "Zep", "Opta")
        ]
    adapters: Iterable[_Adapter] = (
        SofaScoreLeagueAdapter(tournament_id=provider_config["sofascore"], competition_name=provider_config["name"], get=get),
        FotMobLeagueAdapter(season=f"{season[:4]}/{int(season[:4]) + 1}", competition_id=provider_config["fotmob"], competition_name=provider_config["fotmobName"], country=provider_config["country"], get=get),
        Scores365LeagueAdapter(competition_id=provider_config["scores365"], competition_name=provider_config["name"], get=get),
        YouTubeLeagueAdapter(api_key=settings.youtube_api_key, competition_name=provider_config["name"], get=get),
        ZepLeagueAdapter(api_key=settings.zep_api_key, graph_id=graph_id, competition_name=provider_config["name"], get=get),
        OptaLeagueAdapter(api_key=settings.opta_api_key, base_url=settings.opta_base_url, competition_code=provider_config["opta"], competition_name=provider_config["name"], get=get),
    )

    def run(adapter: _Adapter) -> ProviderEvidence:
        try:
            return adapter.collect(home, away, kickoff)  # type: ignore[attr-defined]
        except Exception as exc:
            return ProviderEvidence(adapter.provider, ERROR, adapter.provider, _now(), f"adapter failed: {exc.__class__.__name__}", {})

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(run, adapters))
    return [row.as_dict() for row in rows]


def specialist_reports(provider_evidence: Iterable[dict[str, Any]], *, fotmob_adjustment_applied: bool = False, form_numeric: bool = False) -> list[dict[str, Any]]:
    """Expose World-Cup-shaped specialist reports without inventing signals."""
    by_provider = {str(row.get("provider")): row for row in provider_evidence}
    reports = [
        {"name": "Statistical", "status": "active", "numericContribution": True, "source": "ESPN completed results", "freshness": "pre-kickoff", "reason": "League Poisson baseline."},
        {"name": "Recent form", "status": "active" if form_numeric else "evidence-only", "numericContribution": form_numeric, "source": "ESPN completed results", "freshness": "pre-kickoff", "reason": "Five-match points form is included in the baseline." if form_numeric else "Displayed as context; its fitted-model coefficient is zero."},
    ]
    for name, provider, reason in (("Tactical", "Zep", "Club tactical context."), ("Squad quality", "Opta", "Verified club squad context."), ("Live data", "SofaScore", "Verified pre-kickoff club match context."), ("Market signals", "365Scores", "Verified pre-kickoff market context."), ("Video intelligence", "YouTube", "Verified pre-kickoff team video metadata.")):
        evidence = by_provider.get(provider, {})
        status = evidence.get("status", UNAVAILABLE)
        reports.append({"name": name, "status": status, "numericContribution": False, "source": evidence.get("source", provider), "freshness": evidence.get("fetchedAt", "unknown"), "reason": reason if status == ADMITTED else evidence.get("reason", "No verified pre-kickoff evidence available.")})
    fotmob = by_provider.get("FotMob", {})
    reports[4].update({"source": fotmob.get("source", "FotMob admission gate"), "freshness": fotmob.get("fetchedAt", "unknown"), "status": "active" if fotmob_adjustment_applied else "evidence-only", "numericContribution": fotmob_adjustment_applied})
    return reports

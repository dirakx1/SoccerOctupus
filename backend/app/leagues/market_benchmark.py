"""Fixture-reconciled historical closing-odds benchmarks."""

from __future__ import annotations

import csv
import io
import json
import math
import os
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests


COMPETITION_CODES = {"premier-league": "E0", "la-liga": "SP1", "bundesliga": "D1"}
TEAM_ALIASES = {
    "bournemouth": "afc bournemouth",
    "brighton": "brighton hove albion",
    "man city": "manchester city",
    "man united": "manchester united",
    "newcastle": "newcastle united",
    "nott m forest": "nottingham forest",
    "tottenham": "tottenham hotspur",
    "west ham": "west ham united",
    "wolves": "wolverhampton wanderers",
    "luton": "luton town",
    "ipswich": "ipswich town",
    "leicester": "leicester city",
    "leeds": "leeds united",
    "vallecano": "rayo vallecano",
    "ath bilbao": "athletic club",
    "ath madrid": "atletico madrid",
    "celta": "celta vigo",
    "betis": "real betis",
    "sociedad": "real sociedad",
    "valladolid": "real valladolid",
    "espanol": "espanyol",
    "oviedo": "real oviedo",
    "dortmund": "borussia dortmund",
    "m gladbach": "borussia monchengladbach",
    "leverkusen": "bayer leverkusen",
    "ein frankfurt": "eintracht frankfurt",
    "freiburg": "sc freiburg",
    "heidenheim": "1 fc heidenheim 1846",
    "hoffenheim": "tsg hoffenheim",
    "union berlin": "1 fc union berlin",
    "wolfsburg": "vfl wolfsburg",
    "bochum": "vfl bochum",
    "augsburg": "fc augsburg",
    "fc koln": "fc cologne",
    "hamburg": "hamburg sv",
    "darmstadt": "sv darmstadt 98",
    "stuttgart": "vfb stuttgart",
}


def _name(value: Any) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    normalized = " ".join("".join(character if character.isalnum() else " " for character in ascii_value.lower()).split())
    return TEAM_ALIASES.get(normalized, normalized)


def _probabilities(row: dict[str, str], columns: tuple[str, str, str]) -> dict[str, float] | None:
    try:
        odds = [float(row[column]) for column in columns]
    except (KeyError, TypeError, ValueError):
        return None
    if any(not math.isfinite(value) or value <= 1 for value in odds):
        return None
    raw = [1 / value for value in odds]
    total = sum(raw)
    return {key: round(value / total, 6) for key, value in zip(("home", "draw", "away"), raw)} | {"margin": round(total - 1, 6)}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ClosingOddsAuditor:
    base_url = "https://www.football-data.co.uk/mmz4281/{season}/{competition}.csv"

    def __init__(self, *, get: Callable[..., Any] = requests.get, timeout: float = 20):
        self.get = get
        self.timeout = timeout

    def run(self, season) -> dict[str, Any]:
        competition_code = COMPETITION_CODES.get(season.competition)
        if competition_code is None:
            raise ValueError(f"closing-odds benchmark does not support {season.competition}")
        start, end = season.season.split("-")
        season_code = f"{start[-2:]}{end[-2:]}"
        url = self.base_url.format(season=season_code, competition=competition_code)
        response = self.get(url, timeout=self.timeout)
        response.raise_for_status()
        text = response.content.decode("utf-8-sig") if hasattr(response, "content") else response.text
        rows = list(csv.DictReader(io.StringIO(text)))
        teams = {_name(team["name"]): str(team["id"]) for team in season.teams}
        fixtures = [fixture for fixture in season.fixtures if fixture.get("status") == "completed"]
        records = []
        quarantined = []
        matched: set[str] = set()
        for row in rows:
            try:
                match_date = datetime.strptime(row["Date"], "%d/%m/%Y").replace(tzinfo=timezone.utc)
                home_score, away_score = int(row["FTHG"]), int(row["FTAG"])
            except (KeyError, TypeError, ValueError):
                quarantined.append({"reason": "row has malformed identity, date, or score"})
                continue
            home_id, away_id = teams.get(_name(row.get("HomeTeam"))), teams.get(_name(row.get("AwayTeam")))
            if not home_id or not away_id:
                quarantined.append({"home": row.get("HomeTeam"), "away": row.get("AwayTeam"), "reason": "club identity did not match ESPN"})
                continue
            candidates = []
            for fixture in fixtures:
                kickoff = datetime.fromisoformat(str(fixture["kickoff"]).replace("Z", "+00:00"))
                if (
                    str(fixture["homeTeamId"]) == home_id
                    and str(fixture["awayTeamId"]) == away_id
                    and abs((kickoff.date() - match_date.date()).days) <= 1
                    and int(fixture["homeScore"]) == home_score
                    and int(fixture["awayScore"]) == away_score
                ):
                    candidates.append(fixture)
            if len(candidates) != 1:
                quarantined.append({"home": row.get("HomeTeam"), "away": row.get("AwayTeam"), "date": row.get("Date"), "reason": "no unique ESPN fixture matched"})
                continue
            opening = _probabilities(row, ("AvgH", "AvgD", "AvgA"))
            closing = _probabilities(row, ("AvgCH", "AvgCD", "AvgCA"))
            if opening is None or closing is None:
                quarantined.append({"home": row.get("HomeTeam"), "away": row.get("AwayTeam"), "date": row.get("Date"), "reason": "average opening or closing odds unavailable"})
                continue
            fixture = candidates[0]
            fixture_id = str(fixture["id"])
            matched.add(fixture_id)
            records.append({
                "fixtureId": fixture_id,
                "kickoff": fixture["kickoff"],
                "homeTeamId": home_id,
                "awayTeamId": away_id,
                "actual": "home" if home_score > away_score else "away" if home_score < away_score else "draw",
                "opening": opening,
                "closing": closing,
            })
        for fixture in fixtures:
            if str(fixture["id"]) not in matched:
                quarantined.append({"fixtureId": str(fixture["id"]), "reason": "ESPN fixture has no reconciled market benchmark"})
        result = {
            "provider": "football-data.co.uk",
            "competition": season.competition,
            "season": season.season,
            "source": url,
            "usage": "benchmark-only; closing prices are never historical model inputs",
            "fixtureCount": len(fixtures),
            "reconciledCount": len(records),
            "quarantinedCount": len(quarantined),
            "fixtures": sorted(records, key=lambda item: item["kickoff"]),
            "quarantine": quarantined,
        }
        _write(season.directory / "market-benchmark.json", result)
        return result

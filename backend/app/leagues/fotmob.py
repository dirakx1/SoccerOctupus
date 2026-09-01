"""Compact historical FotMob audit and leakage-safe admission report."""

from __future__ import annotations

import json
import math
import os
import random
import re
import tempfile
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import requests

from .prediction import LeaguePredictionModel, _outcomes

FOTMOB_LEAGUE_URL = "https://www.fotmob.com/api/data/leagues"
FOTMOB_MATCH_URL = "https://www.fotmob.com/api/data/matchDetails"
FOTMOB_HEADERS = {
    "Accept": "application/json",
    "Referer": "https://www.fotmob.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
}
SEASON_IDS = {"2023-24": "2023/2024", "2024-25": "2024/2025", "2025-26": "2025/2026"}
FOTMOB_COMPETITIONS = {
    "premier-league": {"id": 47, "name": "Premier League"},
    "la-liga": {"id": 87, "name": "LaLiga"},
    "bundesliga": {"id": 54, "name": "Bundesliga"},
}
TEAM_NAME_ALIASES = {
    "la-liga": {
        "deportivo alaves": "alaves",
    },
    "bundesliga": {
        "1 fc koln": "fc cologne",
        "augsburg": "fc augsburg",
        "bayern munchen": "bayern munich",
        "bochum": "vfl bochum",
        "fc heidenheim": "1 fc heidenheim 1846",
        "freiburg": "sc freiburg",
        "hamburger sv": "hamburg sv",
        "hoffenheim": "tsg hoffenheim",
        "mainz 05": "mainz",
        "union berlin": "1 fc union berlin",
        "wolfsburg": "vfl wolfsburg",
    },
}
MATCH_TOLERANCE = timedelta(minutes=15)


def _name(value: Any) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()


def _team_name(competition: str, value: Any) -> str:
    normalized = _name(value)
    return TEAM_NAME_ALIASES.get(competition, {}).get(normalized, normalized)


def _dt(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _score(value: Any) -> tuple[int, int] | None:
    match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", str(value or ""))
    return (int(match.group(1)), int(match.group(2))) if match else None


def _write_json(path: Path, value: Any) -> None:
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


def _stat_values(payload: dict[str, Any]) -> dict[str, float | int]:
    groups = payload.get("content", {}).get("stats", {}).get("Periods", {}).get("All", {}).get("stats", [])
    wanted = {
        "expected_goals": "xg",
        "total_shots": "shots",
        "ShotsOnTarget": "shotsOnTarget",
    }
    result: dict[str, float | int] = {}
    for group in groups if isinstance(groups, list) else []:
        for row in group.get("stats", []) if isinstance(group, dict) else []:
            key = row.get("key") if isinstance(row, dict) else None
            values = row.get("stats") if isinstance(row, dict) else None
            output = wanted.get(key)
            if not output or not isinstance(values, list) or len(values) != 2 or output in result:
                continue
            try:
                parsed = [float(item) for item in values]
            except (TypeError, ValueError):
                continue
            result[f"{output}Home"] = int(parsed[0]) if parsed[0].is_integer() else parsed[0]
            result[f"{output}Away"] = int(parsed[1]) if parsed[1].is_integer() else parsed[1]
    return result


class FotMobHistoricalAuditor:
    """Reconcile one committed ESPN edition to FotMob without retaining raw payloads."""

    def __init__(self, *, get: Callable[..., Any] = requests.get, workers: int = 4, delay: float = 0.08, timeout: float = 20):
        self.get = get
        self.workers = max(1, min(workers, 4))
        self.delay = max(0.0, delay)
        self.timeout = timeout

    def _json(self, url: str, **kwargs: Any) -> Any:
        response = self.get(url, timeout=self.timeout, headers=FOTMOB_HEADERS, **kwargs)
        response.raise_for_status()
        return response.json()

    def _details(self, provider_id: str) -> tuple[dict[str, float | int], str | None]:
        if self.delay:
            time.sleep(self.delay)
        try:
            payload = self._json(FOTMOB_MATCH_URL, params={"matchId": provider_id})
            return _stat_values(payload), None
        except (requests.RequestException, TypeError, ValueError) as exc:
            return {}, exc.__class__.__name__

    @staticmethod
    def _fixture_index(season) -> dict[tuple[str, str], list[dict[str, Any]]]:
        index: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for fixture in season.fixtures:
            if fixture.get("status") != "completed":
                continue
            key = (str(fixture["homeTeamId"]), str(fixture["awayTeamId"]))
            index.setdefault(key, []).append(fixture)
        return index

    def run(self, season, *, refresh: bool = False) -> dict[str, Any]:
        if season.season not in SEASON_IDS:
            raise ValueError(f"FotMob historical audit supports {', '.join(SEASON_IDS)}")
        competition = getattr(season, "competition", "premier-league")
        provider = FOTMOB_COMPETITIONS.get(competition)
        if provider is None:
            raise ValueError(f"FotMob historical audit does not support {competition}")
        path = season.directory / "fotmob.json"
        existing = {} if refresh or not path.exists() else json.loads(path.read_text(encoding="utf-8"))
        fetched_at = datetime.now(timezone.utc).isoformat()
        payload = self._json(FOTMOB_LEAGUE_URL, params={"id": provider["id"], "season": SEASON_IDS[season.season]})
        details = payload.get("details", {}) if isinstance(payload, dict) else {}
        if details.get("id") != provider["id"] or details.get("name") != provider["name"] or details.get("selectedSeason") != SEASON_IDS[season.season]:
            raise ValueError(f"FotMob response did not verify the requested {competition} season")
        matches = payload.get("fixtures", {}).get("allMatches", []) if isinstance(payload, dict) else []
        canonical = {_name(team["name"]): team for team in season.teams}
        provider_names: dict[str, str] = {}
        by_pair = self._fixture_index(season)
        records: list[dict[str, Any]] = []
        quarantine: list[dict[str, str]] = []
        matched_espn_ids: set[str] = set()
        seen_espn_ids: set[str] = set()
        cached = {str(item.get("providerFixtureId")): item for item in existing.get("fixtures", [])}
        detail_jobs: dict[str, dict[str, Any]] = {}
        for item in matches if isinstance(matches, list) else []:
            home, away = item.get("home", {}), item.get("away", {})
            provider_id = str(item.get("id", ""))
            home_name, away_name = _team_name(competition, home.get("name")), _team_name(competition, away.get("name"))
            reason = None
            if not provider_id or home_name not in canonical or away_name not in canonical:
                reason = "provider club identity did not uniquely match committed ESPN clubs"
            elif not home.get("id") or not away.get("id"):
                reason = "provider club IDs are missing"
            else:
                provider_names.setdefault(str(home["id"]), home_name)
                provider_names.setdefault(str(away["id"]), away_name)
                if provider_names[str(home["id"])] != home_name or provider_names[str(away["id"])] != away_name:
                    reason = "provider club ID mapped to conflicting names"
            status = item.get("status", {})
            kickoff = _dt(status.get("utcTime"))
            score = _score(status.get("scoreStr"))
            if not reason and (not status.get("finished") or status.get("cancelled") or not kickoff or not score):
                reason = "provider fixture is not a completed, scored match"
            candidates = []
            if not reason:
                home_id, away_id = canonical[home_name]["id"], canonical[away_name]["id"]
                candidates = [fixture for fixture in by_pair.get((str(home_id), str(away_id)), ()) if abs(_dt(fixture["kickoff"]) - kickoff) <= MATCH_TOLERANCE]
                if len(candidates) != 1:
                    reason = "no unique ESPN fixture within fifteen-minute kickoff tolerance"
            if not reason and (candidates[0]["homeScore"], candidates[0]["awayScore"]) != score:
                reason = "FotMob score conflicts with ESPN canonical score"
            if candidates:
                seen_espn_ids.add(str(candidates[0]["id"]))
            if not reason and str(candidates[0]["id"]) in matched_espn_ids:
                reason = "multiple FotMob fixtures reconciled to one ESPN fixture"
            if reason:
                quarantine.append({"providerFixtureId": provider_id, "reason": reason})
                continue
            fixture = candidates[0]
            matched_espn_ids.add(str(fixture["id"]))
            normalized = {
                "providerFixtureId": provider_id,
                "espnFixtureId": str(fixture["id"]),
                "homeTeamId": str(fixture["homeTeamId"]),
                "awayTeamId": str(fixture["awayTeamId"]),
                "homeTeam": fixture["homeTeam"]["name"],
                "awayTeam": fixture["awayTeam"]["name"],
                "kickoff": fixture["kickoff"],
                "availableAfter": (_dt(fixture["kickoff"]) + timedelta(hours=3)).isoformat(),
                "backfilledAt": fetched_at,
                "homeScore": int(score[0]),
                "awayScore": int(score[1]),
                "availableAt": fetched_at,
            }
            previous = cached.get(provider_id, {})
            if previous.get("stats"):
                normalized["stats"] = previous["stats"]
                if previous.get("statsFetchedAt"):
                    normalized["statsFetchedAt"] = previous["statsFetchedAt"]
            else:
                detail_jobs[provider_id] = normalized
            records.append(normalized)
        for fixture in season.fixtures:
            if fixture.get("status") == "completed" and str(fixture["id"]) not in seen_espn_ids:
                quarantine.append({"espnFixtureId": str(fixture["id"]), "reason": "ESPN completed fixture was missing from FotMob season payload"})
        fetched_details_at = datetime.now(timezone.utc).isoformat()
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self._details, provider_id): provider_id for provider_id in detail_jobs}
            for future in as_completed(futures):
                provider_id = futures[future]
                stats, error = future.result()
                record = detail_jobs[provider_id]
                if stats:
                    record["stats"] = stats
                    record["statsFetchedAt"] = fetched_details_at
                elif error:
                    record["statsError"] = error
        records.sort(key=lambda item: item["kickoff"])
        result = {
            "provider": "fotmob",
            "competition": competition,
            "season": season.season,
            "providerSeason": SEASON_IDS[season.season],
            "fetchedAt": fetched_at,
            "fixtureCount": len(matches) if isinstance(matches, list) else 0,
            "reconciledCount": len(records),
            "quarantinedCount": len(quarantine),
            "statsCoverage": sum(1 for item in records if item.get("stats")),
            "xgCoverage": sum(1 for item in records if item.get("stats", {}).get("xgHome") is not None and item.get("stats", {}).get("xgAway") is not None),
            "shotsCoverage": sum(1 for item in records if item.get("stats", {}).get("shotsHome") is not None and item.get("stats", {}).get("shotsAway") is not None),
            "fixtures": records,
            "quarantine": quarantine,
        }
        _write_json(path, result)
        return result


def _probability_metrics(rows: list[tuple[dict[str, float], str]]) -> dict[str, float | int | None]:
    if not rows:
        return {"matches": 0, "logLoss": None, "brier": None, "topLabelCalibrationError": None}
    log_loss = -sum(math.log(max(1e-12, probabilities[actual])) for probabilities, actual in rows) / len(rows)
    brier = sum(sum((probabilities[key] - (key == actual)) ** 2 for key in ("home", "draw", "away")) for probabilities, actual in rows) / len(rows)
    bins: dict[int, list[tuple[float, bool]]] = {}
    for probabilities, actual in rows:
        confidence = max(probabilities.values())
        bins.setdefault(min(9, int(confidence * 10)), []).append((confidence, probabilities[actual] == confidence))
    calibration = sum(len(bucket) / len(rows) * abs(sum(value for value, _ in bucket) / len(bucket) - sum(correct for _, correct in bucket) / len(bucket)) for bucket in bins.values())
    return {"matches": len(rows), "logLoss": round(log_loss, 6), "brier": round(brier, 6), "topLabelCalibrationError": round(calibration, 6)}


def _paired_bootstrap(baseline_rows: list[tuple[dict[str, float], str]], candidate_rows: list[tuple[dict[str, float], str]], *, reps: int = 2000, seed: int = 20260829) -> dict[str, Any]:
    """Resample per-fixture loss improvements; positive means candidate wins."""
    if not baseline_rows or len(baseline_rows) != len(candidate_rows):
        return {"matches": 0, "repetitions": reps, "logLossImprovement": None, "logLossCI95": [None, None], "brierImprovement": None, "brierCI95": [None, None]}
    deltas: list[tuple[float, float]] = []
    for (baseline, actual), (candidate, _) in zip(baseline_rows, candidate_rows):
        baseline_log = -math.log(max(1e-12, baseline[actual]))
        candidate_log = -math.log(max(1e-12, candidate[actual]))
        baseline_brier = sum((baseline[key] - (key == actual)) ** 2 for key in ("home", "draw", "away"))
        candidate_brier = sum((candidate[key] - (key == actual)) ** 2 for key in ("home", "draw", "away"))
        deltas.append((baseline_log - candidate_log, baseline_brier - candidate_brier))
    rng = random.Random(seed)
    samples_log: list[float] = []
    samples_brier: list[float] = []
    for _ in range(reps):
        sample = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        samples_log.append(sum(item[0] for item in sample) / len(sample))
        samples_brier.append(sum(item[1] for item in sample) / len(sample))
    samples_log.sort()
    samples_brier.sort()
    low, high = int(reps * 0.025), int(reps * 0.975) - 1
    return {
        "matches": len(deltas),
        "repetitions": reps,
        "logLossImprovement": round(sum(item[0] for item in deltas) / len(deltas), 6),
        "logLossCI95": [round(samples_log[low], 6), round(samples_log[high], 6)],
        "brierImprovement": round(sum(item[1] for item in deltas) / len(deltas), 6),
        "brierCI95": [round(samples_brier[low], 6), round(samples_brier[high], 6)],
    }


def _candidate_prediction(model: LeaguePredictionModel, fixture: dict[str, Any], records: dict[str, dict[str, Any]]) -> tuple[dict[str, float], bool]:
    baseline = model.predict(fixture["homeTeamId"], fixture["awayTeamId"], kickoff=_dt(fixture["kickoff"]))
    kickoff = _dt(fixture["kickoff"])
    prior: dict[str, list[dict[str, float]]] = {str(fixture["homeTeamId"]): [], str(fixture["awayTeamId"]): []}
    for record in records.values():
        available_after = _dt(record.get("availableAfter"))
        if not record.get("stats") or not available_after or available_after >= kickoff:
            continue
        for team_id, side in ((record["homeTeamId"], "Home"), (record["awayTeamId"], "Away")):
            if team_id in prior:
                prior[team_id].append({"xg": float(record["stats"].get(f"xg{side}", 0)), "shots": float(record["stats"].get(f"shots{side}", 0))})
    if min(len(prior[str(fixture["homeTeamId"])]), len(prior[str(fixture["awayTeamId"])])) < 3:
        return baseline["probabilities"], False
    all_prior = [item for values in prior.values() for item in values]
    league_xg = sum(item["xg"] for item in all_prior) / max(1, len(all_prior))
    league_shots = sum(item["shots"] for item in all_prior) / max(1, len(all_prior))
    if league_xg <= 0 or league_shots <= 0:
        return baseline["probabilities"], False
    factors = []
    for team_id in (str(fixture["homeTeamId"]), str(fixture["awayTeamId"])):
        values = prior[team_id][-5:]
        xg_factor = (sum(item["xg"] for item in values) / len(values)) / league_xg
        shots_factor = (sum(item["shots"] for item in values) / len(values)) / league_shots
        factors.append(min(1.35, max(0.7, 0.7 * xg_factor + 0.3 * shots_factor)))
    expected = baseline["expectedGoals"]
    home_xg = min(4.0, max(0.2, expected["home"] * (1 + 0.2 * (factors[0] - 1))))
    away_xg = min(4.0, max(0.2, expected["away"] * (1 + 0.2 * (factors[1] - 1))))
    rho = 0.0 if baseline.get("modelVersion") == "league-online-poisson-2026.1" else model._fit(kickoff)[4]
    return _outcomes(home_xg, away_xg, rho)[0], True


def admission_report(seasons: dict[str, Any], lower_seasons: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate a fixed xG/shots candidate, tuning nothing on the holdout."""
    lower_seasons = lower_seasons or {}
    reports = {}
    holdout_baseline_rows: list[tuple[dict[str, float], str]] = []
    holdout_candidate_rows: list[tuple[dict[str, float], str]] = []
    for season_name, season in seasons.items():
        audit_path = season.directory / "fotmob.json"
        if not audit_path.exists():
            continue
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        records = {str(item["espnFixtureId"]): item for item in audit.get("fixtures", []) if item.get("stats")}
        promoted_ids = set(season.promoted_team_ids)
        previous_names = sorted(name for name in seasons if name < season_name)
        lower_name = previous_names[-1] if previous_names else None
        lower = lower_seasons.get(lower_name) if lower_name else None
        if not promoted_ids and previous_names:
            previous_ids = {str(team["id"]) for team in seasons[previous_names[-1]].teams}
            lower_ids = {str(team["id"]) for team in lower.teams} if lower else set()
            promoted_ids = ({str(team["id"]) for team in season.teams} - previous_ids) & lower_ids
        competition = season.competition
        historical = [
            {**fixture, "_competition": competition, "_season": prior_name}
            for prior_name, prior in seasons.items()
            if prior_name < season_name
            for fixture in prior.fixtures
            if fixture.get("status") == "completed"
        ]
        if lower is not None:
            historical.extend(
                {**fixture, "_competition": lower.competition, "_season": lower.season}
                for fixture in lower.fixtures
                if fixture.get("status") == "completed"
            )
        current = [
            {**fixture, "_competition": competition, "_season": season_name}
            for fixture in season.fixtures
            if fixture.get("status") == "completed"
        ]
        model = LeaguePredictionModel(
            teams=season.teams,
            completed_fixtures=historical + current,
            promoted_team_ids=promoted_ids,
            competition=competition,
        )
        baseline_rows: list[tuple[dict[str, float], str]] = []
        candidate_rows: list[tuple[dict[str, float], str]] = []
        promoted_baseline_rows: list[tuple[dict[str, float], str]] = []
        promoted_candidate_rows: list[tuple[dict[str, float], str]] = []
        for fixture in season.fixtures:
            if fixture.get("status") != "completed":
                continue
            kickoff = _dt(fixture["kickoff"])
            actual = "home" if fixture["homeScore"] > fixture["awayScore"] else "away" if fixture["homeScore"] < fixture["awayScore"] else "draw"
            baseline = model.predict(fixture["homeTeamId"], fixture["awayTeamId"], kickoff=kickoff)["probabilities"]
            candidate, eligible = _candidate_prediction(model, fixture, records)
            if eligible:
                baseline_rows.append((baseline, actual))
                candidate_rows.append((candidate, actual))
                if str(fixture["homeTeamId"]) in promoted_ids or str(fixture["awayTeamId"]) in promoted_ids:
                    promoted_baseline_rows.append((baseline, actual))
                    promoted_candidate_rows.append((candidate, actual))
        if season_name == "2025-26":
            holdout_baseline_rows = baseline_rows
            holdout_candidate_rows = candidate_rows
        promoted_metrics = _probability_metrics(promoted_candidate_rows)
        if not promoted_candidate_rows:
            promoted_metrics["reason"] = "promoted-team IDs unavailable or insufficient in this edition"
        reports[season_name] = {
            "baseline": _probability_metrics(baseline_rows),
            "candidate": _probability_metrics(candidate_rows),
            "candidateMatches": len(candidate_rows),
            "xgCoverage": sum(1 for item in records.values() if item.get("stats", {}).get("xgHome") is not None and item.get("stats", {}).get("xgAway") is not None),
            "shotsCoverage": sum(1 for item in records.values() if item.get("stats", {}).get("shotsHome") is not None and item.get("stats", {}).get("shotsAway") is not None),
            "scorelineCoverage": len(season.completed_fixtures),
            "promotedTeamIds": sorted(promoted_ids),
            "promotedSubset": {"baseline": _probability_metrics(promoted_baseline_rows), "candidate": promoted_metrics},
        }
    holdout = reports.get("2025-26", {})
    base, candidate = holdout.get("baseline", {}), holdout.get("candidate", {})
    # The report is intentionally a single holdout gate: bootstrap is never
    # used to tune the candidate and is resampled with a fixed seed.
    holdout_bootstrap = _paired_bootstrap(holdout_baseline_rows, holdout_candidate_rows)
    pass_gate = bool(
        candidate.get("matches", 0) >= 100
        and candidate.get("logLoss") is not None
        and base.get("logLoss") is not None
        and candidate["logLoss"] < base["logLoss"]
        and candidate["brier"] < base["brier"]
        and candidate["topLabelCalibrationError"] <= base["topLabelCalibrationError"] + 0.02
        and holdout_bootstrap["logLossCI95"][0] > 0
        and holdout_bootstrap["brierCI95"][0] > 0
    )
    return {
        "version": "fotmob-admission-2026.2",
        "competition": next(iter(seasons.values())).competition if seasons else None,
        "provider": "FotMob",
        "featureSet": "rolling five-match xG/shots, 20% bounded blend",
        "developmentSeason": "2024-25",
        "candidateSelection": "fixed candidate; no parameter tuning",
        "holdoutSeason": "2025-26",
        "adjustmentsApplied": pass_gate,
        "gate": {"passed": pass_gate, "requirements": ["holdout log loss improves with positive 95% paired bootstrap CI", "holdout Brier improves with positive 95% paired bootstrap CI", "top-label calibration error not >0.02 worse", "at least 100 eligible holdout matches"]},
        "holdoutBootstrap": holdout_bootstrap,
        "seasons": reports,
    }

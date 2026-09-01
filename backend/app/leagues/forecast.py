"""Edition-scoped immutable forecast snapshots and resolved metrics."""

from __future__ import annotations

import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .evidence import collect_league_evidence
from .prediction import LeaguePredictionModel, admitted_fotmob_records
from .swarm import build_league_swarm, provider_signal


LEDGER_VERSION = 2
PROVIDERS = ("SofaScore", "FotMob", "365Scores", "YouTube", "Zep", "Opta")


def _dt(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _actual(home_score: int, away_score: int) -> str:
    return "home" if home_score > away_score else "away" if home_score < away_score else "draw"


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": LEDGER_VERSION, "forecasts": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": LEDGER_VERSION, "forecasts": []}
    return value if isinstance(value, dict) and isinstance(value.get("forecasts"), list) else {"version": LEDGER_VERSION, "forecasts": []}


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _admitted_provider_weights(season) -> dict[str, float]:
    """Read only provider weights that passed this edition's persisted gate."""
    try:
        report = json.loads((season.directory / "provider-admission.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if report.get("version") != 1:
        return {}
    return {
        str(row["provider"]): float(row["weight"])
        for row in report.get("providers", ())
        if row.get("passed") is True and float(row.get("weight", 0.0)) > 0
    }


def _provider_snapshot(forecast: dict[str, Any], *, season, kickoff: datetime, settings: Any) -> None:
    """Attach the one pre-kickoff provider snapshot used for later calibration."""
    if settings is None:
        return
    evidence = collect_league_evidence(
        home=forecast["homeTeam"]["name"],
        away=forecast["awayTeam"]["name"],
        kickoff=kickoff,
        competition=season.competition,
        season=season.season,
        graph_id=str(season.edition.get("leagueGraph", {}).get("graphId", "")),
        settings=settings,
    )
    forecast["baselineProbabilities"] = dict(forecast["probabilities"])
    swarm = build_league_swarm(forecast, evidence, calibrated_weights=_admitted_provider_weights(season))
    forecast["probabilities"] = swarm["probabilities"]
    forecast["modelVersion"] = swarm["modelVersion"]
    outcome = max(swarm["probabilities"], key=swarm["probabilities"].get)
    forecast["outcome"] = {"home": "home_win", "draw": "draw", "away": "away_win"}[outcome]
    forecast["confidence"] = round(swarm["probabilities"][outcome], 4)
    forecast["evidence"] = {
        **forecast.get("evidence", {}),
        "providerEvidence": evidence,
        "swarmModelVersion": swarm["modelVersion"],
    }
    forecast["analysis"] = {
        **forecast.get("analysis", {}),
        "specialists": swarm["specialists"],
        "swarm": {
            "modelVersion": swarm["modelVersion"],
            "contributions": swarm["contributions"],
            "abstentions": swarm["abstentions"],
        },
    }


def fixture_forecast(season, fixture: dict[str, Any], kickoff: datetime, *, settings: Any = None) -> dict[str, Any]:
    """Return the canonical fixture forecast used by prediction, markets, and the ledger."""
    model = LeaguePredictionModel(
        teams=season.teams,
        completed_fixtures=season.completed_fixtures,
        promoted_team_ids=season.promoted_team_ids,
        fotmob_records=admitted_fotmob_records(season),
        competition=season.competition,
    )
    forecast = model.predict(fixture["homeTeamId"], fixture["awayTeamId"], kickoff=kickoff)
    forecast["evidence"] = {
        **forecast.get("evidence", {}),
        "numericalFoundation": "ESPN completed results",
        "adjustmentsApplied": bool(forecast.get("evidence", {}).get("fotmobAdjustmentApplied")),
        "adjustmentVersion": forecast.get("evidence", {}).get("fotmobAdjustmentVersion"),
    }
    _provider_snapshot(forecast, season=season, kickoff=kickoff, settings=settings)
    return forecast


def sync_forecast_ledger(season, *, now: datetime | None = None, settings: Any = None) -> dict[str, Any]:
    """Snapshot future fixtures and resolve only previously recorded forecasts."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    path = season.directory / "forecasts.json"
    ledger = _read(path)
    rows = ledger["forecasts"]
    indexed = {str(row.get("fixtureId")): row for row in rows}
    changed = False
    for fixture in season.fixtures:
        fixture_id = str(fixture.get("id", ""))
        kickoff = _dt(fixture.get("kickoff"))
        if not fixture_id or kickoff is None:
            continue
        existing = indexed.get(fixture_id)
        if fixture.get("status") == "completed" and fixture.get("homeScore") is not None and fixture.get("awayScore") is not None:
            if existing is not None and "actual" not in existing:
                existing["actual"] = {
                    "homeScore": int(fixture["homeScore"]),
                    "awayScore": int(fixture["awayScore"]),
                    "outcome": _actual(int(fixture["homeScore"]), int(fixture["awayScore"])),
                    "resolvedAt": now.isoformat(),
                }
                changed = True
            continue
        if fixture.get("status") != "scheduled" or kickoff <= now or kickoff - now > timedelta(minutes=35) or existing is not None:
            continue
        forecast = fixture_forecast(season, fixture, kickoff, settings=settings)
        row = {
            "fixtureId": fixture_id,
            "competition": season.competition,
            "season": season.season,
            "homeTeamId": str(fixture["homeTeamId"]),
            "awayTeamId": str(fixture["awayTeamId"]),
            "homeTeamName": forecast["homeTeam"]["name"],
            "awayTeamName": forecast["awayTeam"]["name"],
            "kickoff": fixture["kickoff"],
            "modelVersion": forecast["modelVersion"],
            "generatedAt": now.isoformat(),
            "probabilities": forecast["probabilities"],
            "baselineProbabilities": forecast.get("baselineProbabilities", forecast["probabilities"]),
            "expectedGoals": forecast["expectedGoals"],
            "likelyScore": forecast["likelyScore"],
            "evidence": forecast.get("evidence", {}),
            "analysis": forecast.get("analysis", {}),
            "adjustmentsApplied": bool(forecast.get("evidence", {}).get("fotmobAdjustmentApplied")),
            "adjustmentVersion": forecast.get("evidence", {}).get("fotmobAdjustmentVersion"),
        }
        rows.append(row)
        indexed[fixture_id] = row
        changed = True
    if changed or not path.exists():
        ledger["version"] = LEDGER_VERSION
        ledger["forecasts"] = sorted(rows, key=lambda row: (str(row.get("kickoff", "")), str(row.get("fixtureId", ""))))
        _write(path, ledger)
    return ledger


def forecast_metrics(season) -> dict[str, Any]:
    rows = [row for row in _read(season.directory / "forecasts.json")["forecasts"] if isinstance(row.get("actual"), dict)]
    if not rows:
        return {"status": "insufficient", "sampleSize": 0, "logLoss": None, "brier": None, "topLabelCalibrationError": None, "correctOutcomeRate": None}
    log_loss = 0.0
    brier = 0.0
    correct = 0
    bins: dict[int, list[tuple[float, bool]]] = {}
    for row in rows:
        probabilities = row.get("probabilities", {})
        actual = row["actual"].get("outcome")
        if actual not in probabilities:
            continue
        probability = max(1e-12, float(probabilities[actual]))
        log_loss -= math.log(probability)
        brier += sum((float(probabilities.get(key, 0.0)) - (key == actual)) ** 2 for key in ("home", "draw", "away"))
        predicted = max(probabilities, key=probabilities.get)
        correct += predicted == actual
        confidence = float(probabilities[predicted])
        bins.setdefault(min(9, int(confidence * 10)), []).append((confidence, predicted == actual))
    sample = sum(len(bucket) for bucket in bins.values())
    calibration = sum(len(bucket) / sample * abs(sum(value for value, _ in bucket) / len(bucket) - sum(correct_value for _, correct_value in bucket) / len(bucket)) for bucket in bins.values()) if sample else None
    return {
        "status": "available" if sample >= 30 else "insufficient",
        "sampleSize": sample,
        "logLoss": round(log_loss / sample, 6) if sample else None,
        "brier": round(brier / sample, 6) if sample else None,
        "topLabelCalibrationError": round(calibration, 6) if calibration is not None else None,
        "correctOutcomeRate": round(correct / sample, 6) if sample else None,
    }


def forecast_performance(season) -> dict[str, Any]:
    """Summarize only the immutable provider snapshots available for calibration."""
    rows = _read(season.directory / "forecasts.json")["forecasts"]
    providers = {name: {"provider": name, "snapshots": 0, "resolvedSnapshots": 0, "numericResolvedSnapshots": 0, "statuses": {}, "samples": []} for name in PROVIDERS}
    for row in rows:
        evidence = row.get("evidence", {}).get("providerEvidence", [])
        if not isinstance(evidence, list):
            continue
        resolved = isinstance(row.get("actual"), dict)
        for item in evidence:
            provider = str(item.get("provider", ""))
            if provider not in providers:
                continue
            summary = providers[provider]
            summary["snapshots"] += 1
            summary["resolvedSnapshots"] += int(resolved)
            status = str(item.get("status", "unavailable"))
            summary["statuses"][status] = summary["statuses"].get(status, 0) + 1
            if not resolved:
                continue
            signal = provider_signal(item, home_name=str(row.get("homeTeamName", "")), away_name=str(row.get("awayTeamName", "")))
            baseline = row.get("baselineProbabilities") or row.get("probabilities")
            actual = row["actual"].get("outcome")
            if signal is not None and actual in ("home", "draw", "away") and isinstance(baseline, dict):
                try:
                    normalized_baseline = {key: float(baseline[key]) for key in ("home", "draw", "away")}
                except (KeyError, TypeError, ValueError):
                    continue
                summary["samples"].append((normalized_baseline, signal, actual))
                summary["numericResolvedSnapshots"] += 1
    result = []
    for summary in providers.values():
        samples = summary.pop("samples")
        recommendation = _provider_admission(samples)
        summary.update(recommendation)
        summary["admission"] = "active" if recommendation["passed"] else "not-collected" if not summary["snapshots"] else "collecting" if len(samples) < 60 else "not-admitted"
        result.append(summary)
    _retain_best_provider(result)
    return {
        "snapshots": len(rows),
        "resolvedSnapshots": sum(isinstance(row.get("actual"), dict) for row in rows),
        "accuracy": forecast_metrics(season),
        "baseline": {"provider": "ESPN baseline", "weight": 1.0, "admission": "active"},
        "providers": result,
    }


def _scores(samples: list[tuple[dict[str, float], dict[str, float], str]], weight: float) -> tuple[float, float]:
    log_loss = brier = 0.0
    for baseline, signal, actual in samples:
        probabilities = {key: (baseline[key] + weight * signal[key]) / (1 + weight) for key in ("home", "draw", "away")}
        log_loss -= math.log(max(1e-12, probabilities[actual]))
        brier += sum((probabilities[key] - (key == actual)) ** 2 for key in probabilities)
    return log_loss / len(samples), brier / len(samples)


def _provider_admission(samples: list[tuple[dict[str, float], dict[str, float], str]]) -> dict[str, Any]:
    """Select on older records and gate on the final 30 immutable forecasts."""
    empty = {"weight": 0.0, "passed": False, "developmentSize": 0, "holdoutSize": 0, "holdout": None, "confidenceIntervals": None}
    if len(samples) < 60:
        return empty
    development, holdout = samples[:-30], samples[-30:]
    # Relative provider weights above one allow a demonstrably stronger signal
    # (notably a market consensus) to dominate without special-case logic.
    weights = [value / 20 for value in range(21)] + [1.25, 1.5, 2.0, 3.0, 5.0, 10.0, 100.0]
    weight = min(weights, key=lambda value: _scores(development, value))
    if weight <= 0:
        return {**empty, "developmentSize": len(development), "holdoutSize": len(holdout)}
    baseline_scores = _scores(holdout, 0.0)
    candidate_scores = _scores(holdout, weight)
    rng = random.Random(20260901)
    improvements = []
    for _ in range(1000):
        sample = [holdout[rng.randrange(len(holdout))] for _ in holdout]
        before = _scores(sample, 0.0)
        after = _scores(sample, weight)
        improvements.append((before[0] - after[0], before[1] - after[1]))
    intervals = []
    for index in (0, 1):
        ordered = sorted(row[index] for row in improvements)
        intervals.append([ordered[24], ordered[974]])
    passed = all(interval[0] > 0 for interval in intervals)
    return {
        "weight": weight if passed else 0.0,
        "testedWeight": weight,
        "passed": passed,
        "developmentSize": len(development),
        "holdoutSize": len(holdout),
        "holdout": {"baselineLogLoss": baseline_scores[0], "candidateLogLoss": candidate_scores[0], "baselineBrier": baseline_scores[1], "candidateBrier": candidate_scores[1]},
        "confidenceIntervals": {"logLossImprovement95": intervals[0], "brierImprovement95": intervals[1]},
    }


def _retain_best_provider(providers: list[dict[str, Any]]) -> None:
    """Avoid combining independently calibrated, correlated provider signals."""
    passing = [row for row in providers if row.get("passed") is True]
    if len(passing) <= 1:
        return
    winner = min(passing, key=lambda row: float((row.get("holdout") or {}).get("candidateLogLoss", math.inf)))
    for row in passing:
        if row is winner:
            continue
        row["passed"] = False
        row["weight"] = 0.0
        row["admission"] = "not-admitted"
        row["reason"] = f"A stronger passing provider ({winner['provider']}) was retained to avoid an untested correlated blend."


def provider_admission_report(season) -> dict[str, Any]:
    """Build the exact report consumed by future forecasts for this edition."""
    performance = forecast_performance(season)
    return {
        "version": 1,
        "competition": season.competition,
        "season": season.season,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "rule": "60 numeric resolved snapshots; select on earlier records; final 30 holdout; both paired-bootstrap 95% lower bounds above zero",
        "providers": performance["providers"],
    }

"""Small, auditable multi-agent ensemble for league forecasts.

This module consumes evidence already collected by the league adapters.  It
never fetches data and agents that cannot produce a numerical, pre-kickoff
signal explicitly abstain.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

MODEL_VERSION = "league-swarm-2026.2"

def _normal(values: Iterable[float]) -> dict[str, float] | None:
    try:
        values = [float(v) for v in values]
    except (TypeError, ValueError):
        return None
    if len(values) != 3 or any(not math.isfinite(v) or v < 0 for v in values):
        return None
    total = sum(values)
    if total <= 0:
        return None
    return {key: value / total for key, value in zip(("home", "draw", "away"), values)}


def _poisson(home: float, away: float) -> dict[str, float] | None:
    if not all(math.isfinite(x) and 0 < x <= 5 for x in (home, away)):
        return None
    result = [0.0, 0.0, 0.0]
    for h in range(8):
        for a in range(8):
            p = math.exp(-home) * home**h / math.factorial(h) * math.exp(-away) * away**a / math.factorial(a)
            result[0 if h > a else 2 if h < a else 1] += p
    return _normal(result)


def provider_signal(row: dict[str, Any], *, home_name: str, away_name: str) -> dict[str, float] | None:
    """Return a provider's normalized 1X2 signal, or abstain safely."""
    if row.get("status") != "admitted":
        return None
    evidence = row.get("evidence") or {}
    provider = str(row.get("provider", ""))
    if provider == "365Scores":
        return _normal([evidence.get("homeImplied"), evidence.get("drawImplied"), evidence.get("awayImplied")])
    if provider == "SofaScore":
        home = evidence.get(home_name)
        away = evidence.get(away_name)
        if not isinstance(home, dict) or not isinstance(away, dict):
            return None
        try:
            home_xg = (float(home["goalsForPerMatch"]) + float(away["goalsAgainstPerMatch"])) / 2
            away_xg = (float(away["goalsForPerMatch"]) + float(home["goalsAgainstPerMatch"])) / 2
        except (KeyError, TypeError, ValueError):
            return None
        return _poisson(home_xg, away_xg)
    if provider == "FotMob":
        home, away = evidence.get(home_name), evidence.get(away_name)
        if not isinstance(home, dict) or not isinstance(away, dict):
            return None
        hs, a_s = home.get("stats", {}), away.get("stats", {})
        try:
            hx = (float(hs["goals_team_match"]) + float(a_s["goals_conceded_team_match"])) / 2
            ax = (float(a_s["goals_team_match"]) + float(hs["goals_conceded_team_match"])) / 2
        except (KeyError, TypeError, ValueError):
            return None
        return _poisson(hx, ax)
    return None


def build_league_swarm(
    baseline: dict[str, Any],
    provider_evidence: Iterable[dict[str, Any]] = (),
    *,
    calibrated_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return consensus, contributions, specialist results, and abstentions."""
    probabilities = _normal([baseline.get("probabilities", {}).get(k) for k in ("home", "draw", "away")])
    if probabilities is None:
        raise ValueError("baseline probabilities must be finite and normalizable")
    home_name = str(baseline.get("homeTeam", {}).get("name", ""))
    away_name = str(baseline.get("awayTeam", {}).get("name", ""))
    specialists = [{"name": "Statistical", "status": "active", "weight": 1.0, "source": "ESPN completed results", "probabilities": probabilities}]
    contributions = [{"name": "Statistical", "source": "ESPN completed results", "weight": 1.0}]
    abstentions = []
    weighted = [probabilities[k] for k in ("home", "draw", "away")]
    total_weight = 1.0
    calibrated_weights = calibrated_weights or {}
    for row in provider_evidence:
        provider = str(row.get("provider", "unknown"))
        signal = provider_signal(row, home_name=home_name, away_name=away_name)
        weight = max(0.0, float(calibrated_weights.get(provider, 0.0)))
        if signal is None or weight <= 0:
            reason = row.get("reason", "unavailable or non-numerical evidence")
            if signal is not None and weight <= 0:
                reason = "No completed-fixture calibration has admitted this provider to the consensus."
            abstentions.append({"name": provider, "reason": reason})
            specialists.append({
                "name": provider,
                "status": "evidence-only" if row.get("status") == "admitted" else row.get("status", "unavailable"),
                "weight": 0.0,
                "source": row.get("source", provider),
                "reason": reason,
                "abstained": True,
            })
            continue
        for index, key in enumerate(("home", "draw", "away")):
            weighted[index] += weight * signal[key]
        total_weight += weight
        contributions.append({"name": provider, "source": row.get("source", provider), "weight": weight})
        specialists.append({"name": provider, "status": "active", "weight": weight, "source": row.get("source", provider), "probabilities": signal, "reason": "A persisted leakage-safe admission report includes this provider in the consensus."})
    consensus = _normal([value / total_weight for value in weighted])
    return {"modelVersion": MODEL_VERSION, "baseline": baseline.get("probabilities"), "probabilities": consensus, "specialists": specialists, "contributions": contributions, "abstentions": abstentions}

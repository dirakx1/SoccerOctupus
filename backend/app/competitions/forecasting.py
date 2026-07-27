"""Recency-weighted club baseline and normalized Poisson forecasts.

Each match receives exponential half-life weighting (180 days). Attack and
defence are weighted goals for/against, form is weighted points per possible
point, and strength combines attack, defensive resistance, and form. Clubs
promoted from the Championship receive a documented 0.88 strength multiplier
to account for the division transition until Premier League evidence accrues.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone


MODEL_VERSION = "club-poisson-1"
MIN_MATCHES = 5
PROMOTION_ADJUSTMENT = 0.88


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def build_club_baseline(matches: list[dict], *, promoted: bool, as_of: datetime) -> dict:
    if len(matches) < MIN_MATCHES:
        raise ValueError(f"At least {MIN_MATCHES} completed club matches are required")
    now = _aware(as_of)
    weighted = []
    for match in matches:
        age_days = max((now - _aware(match["played_at"])).total_seconds() / 86400, 0)
        weight = 0.5 ** (age_days / 180)
        goals_for = match["goals_for"]
        goals_against = match["goals_against"]
        points = 3 if goals_for > goals_against else 1 if goals_for == goals_against else 0
        weighted.append((weight, goals_for, goals_against, points))
    total_weight = sum(row[0] for row in weighted)
    attack = sum(weight * goals for weight, goals, _, _ in weighted) / total_weight
    defence = sum(weight * goals for weight, _, goals, _ in weighted) / total_weight
    form = sum(weight * points for weight, _, _, points in weighted) / (3 * total_weight)
    adjustment = PROMOTION_ADJUSTMENT if promoted else 1.0
    strength = (attack + 1 / max(defence, 0.35) + form) / 3 * adjustment
    return {
        "attack": round(attack, 4),
        "defence": round(defence, 4),
        "form": round(form, 4),
        "strength": round(strength, 4),
        "matches": len(matches),
        "promotion_adjustment": adjustment,
    }


def poisson_forecast(*, home_xg: float, away_xg: float, max_goals: int = 7) -> dict:
    rows = []
    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            probability = (
                math.exp(-home_xg) * home_xg**home / math.factorial(home)
                * math.exp(-away_xg) * away_xg**away / math.factorial(away)
            )
            rows.append({"home": home, "away": away, "probability": probability})
    total = sum(row["probability"] for row in rows)
    for row in rows:
        row["probability"] /= total
    outcomes = {
        "home": sum(row["probability"] for row in rows if row["home"] > row["away"]),
        "draw": sum(row["probability"] for row in rows if row["home"] == row["away"]),
        "away": sum(row["probability"] for row in rows if row["home"] < row["away"]),
    }
    likely = max(rows, key=lambda row: row["probability"])
    return {
        "scoreline_distribution": rows,
        "outcome_probabilities": outcomes,
        "expected_goals": {"home": round(home_xg, 3), "away": round(away_xg, 3)},
        "likely_score": f"{likely['home']}-{likely['away']}",
    }

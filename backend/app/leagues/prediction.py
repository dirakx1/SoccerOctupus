from __future__ import annotations

import math
import json
import random
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Iterable


MODEL_VERSION = "league-poisson-2026.1"
FOTMOB_ADJUSTMENT_VERSION = "fotmob-admission-2026.1"


def admitted_fotmob_records(season) -> tuple[dict[str, Any], ...]:
    """Load only the compact historical cache after a persisted gate pass."""
    if season.competition != "premier-league":
        return ()
    root = season.directory.parent.parent
    report_path = root / "fotmob-admission-report.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    if report.get("version") != FOTMOB_ADJUSTMENT_VERSION or report.get("adjustmentsApplied") is not True:
        return ()
    records: list[dict[str, Any]] = []
    for season_name in ("2024-25", "2025-26"):
        try:
            audit = json.loads((root / "premier-league" / season_name / "fotmob.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        records.extend(item for item in audit.get("fixtures", ()) if item.get("stats"))
    return tuple(records)


def _poisson(lam: float, goals: int) -> float:
    return math.exp(-lam) * lam**goals / math.factorial(goals)


def _outcomes(home_xg: float, away_xg: float) -> tuple[dict[str, float], tuple[int, int], float, float]:
    home = draw = away = btts = over25 = 0.0
    best = (0, 0)
    best_probability = -1.0
    for home_goals in range(9):
        for away_goals in range(9):
            probability = _poisson(home_xg, home_goals) * _poisson(away_xg, away_goals)
            if home_goals > away_goals:
                home += probability
            elif home_goals == away_goals:
                draw += probability
            else:
                away += probability
            if home_goals and away_goals:
                btts += probability
            if home_goals + away_goals >= 3:
                over25 += probability
            if probability > best_probability:
                best_probability = probability
                best = (home_goals, away_goals)
    total = home + draw + away
    return ({"home": home / total, "draw": draw / total, "away": away / total}, best, btts, over25)


def _score_probabilities(home_xg: float, away_xg: float, *, limit: int = 9) -> list[dict[str, Any]]:
    """Return the ordered scoreline distribution used by the outcome model."""
    rows = []
    total = 0.0
    for home_goals in range(limit):
        for away_goals in range(limit):
            probability = _poisson(home_xg, home_goals) * _poisson(away_xg, away_goals)
            total += probability
            rows.append((probability, home_goals, away_goals))
    return [
        {"score": f"{home_goals}-{away_goals}", "home": home_goals, "away": away_goals, "probability": probability / total}
        for probability, home_goals, away_goals in sorted(rows, reverse=True)[:5]
    ]


class LeaguePredictionModel:
    """A leakage-safe online league model using only results available before kickoff."""

    def __init__(
        self,
        *,
        teams: Iterable[dict[str, Any]],
        completed_fixtures: Iterable[dict[str, Any]],
        promoted_team_ids: set[str] | None = None,
        fotmob_records: Iterable[dict[str, Any]] = (),
    ):
        self.teams = {str(team["id"]): team for team in teams}
        self.completed = sorted(completed_fixtures, key=lambda item: item["kickoff"])
        self.promoted = promoted_team_ids or set()
        self.fotmob_records = tuple(fotmob_records)

    def _ratings(self, before: datetime) -> tuple[dict[str, float], dict[str, float], dict[str, deque[int]]]:
        attack = defaultdict(float)
        defence = defaultdict(float)
        form: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=5))
        for team_id in self.promoted:
            attack[team_id] = -0.12
            defence[team_id] = -0.08
        for fixture in self.completed:
            kickoff = datetime.fromisoformat(fixture["kickoff"].replace("Z", "+00:00"))
            if kickoff >= before:
                continue
            home, away = str(fixture["homeTeamId"]), str(fixture["awayTeamId"])
            home_score, away_score = int(fixture["homeScore"]), int(fixture["awayScore"])
            expected_home = 1.45 * math.exp(attack[home] - defence[away])
            expected_away = 1.15 * math.exp(attack[away] - defence[home])
            rate = 0.035
            home_error, away_error = home_score - expected_home, away_score - expected_away
            attack[home] += rate * home_error
            defence[away] -= rate * home_error
            attack[away] += rate * away_error
            defence[home] -= rate * away_error
            if home_score > away_score:
                points = (3, 0)
            elif home_score < away_score:
                points = (0, 3)
            else:
                points = (1, 1)
            form[home].append(points[0])
            form[away].append(points[1])
        return attack, defence, form

    def predict(self, home_team_id: str, away_team_id: str, *, kickoff: datetime) -> dict[str, Any]:
        home, away = str(home_team_id), str(away_team_id)
        if home not in self.teams or away not in self.teams or home == away:
            raise ValueError("prediction requires two different registered teams")
        attack, defence, form = self._ratings(kickoff)
        home_form = sum(form[home]) / max(1, len(form[home]))
        away_form = sum(form[away]) / max(1, len(form[away]))
        form_delta = (home_form - away_form) / 3
        home_xg = min(4.0, max(0.2, 1.45 * math.exp(attack[home] - defence[away] + 0.08 * form_delta)))
        away_xg = min(4.0, max(0.2, 1.15 * math.exp(attack[away] - defence[home] - 0.08 * form_delta)))
        adjustment_applied = False
        if self.fotmob_records:
            prior: dict[str, list[dict[str, float]]] = {home: [], away: []}
            for record in self.fotmob_records:
                record_kickoff = datetime.fromisoformat(record["kickoff"].replace("Z", "+00:00"))
                available_after = record.get("availableAfter")
                if not available_after:
                    continue
                available_after_dt = datetime.fromisoformat(available_after.replace("Z", "+00:00"))
                if record_kickoff >= kickoff or available_after_dt >= kickoff or not record.get("stats"):
                    continue
                for team_id, side in ((str(record["homeTeamId"]), "Home"), (str(record["awayTeamId"]), "Away")):
                    if team_id in prior:
                        stats = record["stats"]
                        if f"xg{side}" in stats and f"shots{side}" in stats:
                            prior[team_id].append({"xg": float(stats[f"xg{side}"]), "shots": float(stats[f"shots{side}"])})
            if min(len(prior[home]), len(prior[away])) >= 3:
                prior_values = [item for values in prior.values() for item in values]
                league_xg = sum(item["xg"] for item in prior_values) / len(prior_values)
                league_shots = sum(item["shots"] for item in prior_values) / len(prior_values)
                if league_xg > 0 and league_shots > 0:
                    factors = []
                    for team_id in (home, away):
                        values = prior[team_id][-5:]
                        xg_factor = (sum(item["xg"] for item in values) / len(values)) / league_xg
                        shots_factor = (sum(item["shots"] for item in values) / len(values)) / league_shots
                        factors.append(min(1.35, max(0.7, 0.7 * xg_factor + 0.3 * shots_factor)))
                    home_xg = min(4.0, max(0.2, home_xg * (1 + 0.2 * (factors[0] - 1))))
                    away_xg = min(4.0, max(0.2, away_xg * (1 + 0.2 * (factors[1] - 1))))
                    adjustment_applied = True
        probabilities, score, btts, over25 = _outcomes(home_xg, away_xg)
        confidence = max(probabilities.values())
        outcome = max(probabilities, key=probabilities.get)
        home_points = sum(form[home])
        away_points = sum(form[away])
        signals = [
            {
                "name": "Statistical strength",
                "direction": "home" if home_xg > away_xg else "away" if away_xg > home_xg else "neutral",
                "reason": f"Expected goals are {home_xg:.2f} for {self.teams[home]['name']} and {away_xg:.2f} for {self.teams[away]['name']}.",
                "sources": ["ESPN completed results", "home/away attack and defence"],
            },
            {
                "name": "Recent five-match form",
                "direction": "home" if home_points > away_points else "away" if away_points > home_points else "neutral",
                "reason": f"Recent form points are {home_points} to {away_points} across available completed matches.",
                "sources": ["ESPN completed results"],
            },
            {
                "name": "Home advantage",
                "direction": "home",
                "reason": "The baseline applies a fixed home-venue scoring advantage.",
                "sources": ["league Poisson baseline"],
            },
        ]
        if home in self.promoted or away in self.promoted:
            promoted = self.teams[home if home in self.promoted else away]["name"]
            signals.append({
                "name": "Promoted-team prior",
                "direction": "neutral",
                "reason": f"A conservative promoted-team prior is applied to {promoted}.",
                "sources": ["edition promoted-team metadata"],
            })
        # Keep the league response comparable with the World Cup swarm while
        # making the boundary explicit: only signals backed by this season's
        # pre-kickoff data may affect the league probabilities.  These entries
        # are intentionally evidence-only until a league-specific adapter and
        # backtest admit them numerically.
        specialists = [
            {"name": "Statistical", "status": "active", "numericContribution": True, "sources": ["ESPN completed results"], "reason": "Drives the league Poisson forecast."},
            {"name": "Recent form", "status": "active", "numericContribution": True, "sources": ["ESPN completed results"], "reason": "Uses each club's available pre-kickoff five-match points."},
            {"name": "Tactical", "status": "unavailable", "numericContribution": False, "sources": [], "reason": "No verified fixture-bound tactical dataset is available for this league snapshot."},
            {"name": "Squad quality", "status": "unavailable", "numericContribution": False, "sources": [], "reason": "No verified pre-kickoff squad availability and player-rating snapshot is available."},
            {"name": "Live data", "status": "evidence-only", "numericContribution": False, "sources": ["FotMob admission gate"], "reason": "Admitted FotMob xG/shots can adjust the baseline only after the persisted gate passes."},
            {"name": "Market signals", "status": "unavailable", "numericContribution": False, "sources": [], "reason": "No league market feed has passed the numerical admission gate."},
            {"name": "Video intelligence", "status": "unavailable", "numericContribution": False, "sources": [], "reason": "Video analysis is not verified as a pre-kickoff league input."},
        ]
        favored_name = self.teams[home]["name"] if outcome == "home" else self.teams[away]["name"] if outcome == "away" else "draw"
        return {
            "modelVersion": MODEL_VERSION,
            "generatedAt": datetime.now(kickoff.tzinfo).isoformat(),
            "homeTeam": self.teams[home],
            "awayTeam": self.teams[away],
            "outcome": {"home": "home_win", "draw": "draw", "away": "away_win"}[outcome],
            "probabilities": probabilities,
            "expectedGoals": {"home": round(home_xg, 3), "away": round(away_xg, 3)},
            "likelyScore": {"home": score[0], "away": score[1]},
            "scoreProbabilities": _score_probabilities(home_xg, away_xg),
            "confidence": round(confidence, 4),
            "markets": {
                "bothTeamsToScoreYes": round(btts, 4),
                "over2_5": round(over25, 4),
                "under2_5": round(1 - over25, 4),
                "homeCleanSheet": round(math.exp(-away_xg), 4),
                "awayCleanSheet": round(math.exp(-home_xg), 4),
            },
            "evidence": {
                "completedMatches": sum(1 for item in self.completed if datetime.fromisoformat(item["kickoff"].replace("Z", "+00:00")) < kickoff),
                "promotedPriorApplied": home in self.promoted or away in self.promoted,
                "inputs": ["ESPN completed results", "home/away attack and defence", "five-match form", "promoted-team prior"] + (["FotMob rolling xG/shots"] if adjustment_applied else []),
                "fotmobAdjustmentApplied": adjustment_applied,
                "fotmobAdjustmentVersion": FOTMOB_ADJUSTMENT_VERSION if self.fotmob_records else None,
            },
            "analysis": {
                "summary": f"{favored_name} has the highest baseline outcome probability at {confidence:.0%}.",
                "keyFactors": [signal["reason"] for signal in signals],
                "signals": signals,
                "specialists": specialists,
            },
        }


def _sample_poisson(rng: random.Random, lam: float) -> int:
    threshold = math.exp(-lam)
    product = 1.0
    goals = 0
    while product > threshold:
        goals += 1
        product *= rng.random()
    return goals - 1


def project_table(season, *, simulations: int = 2000, seed: int = 20260829) -> list[dict[str, Any]]:
    teams = {str(team["id"]): team for team in season.teams}
    base = {team_id: {"points": 0, "gf": 0, "ga": 0} for team_id in teams}
    for row in season.standings:
        team_id = str(row["teamId"])
        base[team_id] = {"points": int(row["points"]), "gf": int(row["goalsFor"]), "ga": int(row["goalsAgainst"])}
    remaining = [fixture for fixture in season.fixtures if fixture["status"] == "scheduled"]
    model = LeaguePredictionModel(teams=season.teams, completed_fixtures=season.completed_fixtures, promoted_team_ids=season.promoted_team_ids, fotmob_records=admitted_fotmob_records(season))
    forecasts = []
    for fixture in remaining:
        kickoff = datetime.fromisoformat(fixture["kickoff"].replace("Z", "+00:00"))
        forecasts.append((fixture, model.predict(fixture["homeTeamId"], fixture["awayTeamId"], kickoff=kickoff)))
    totals = {team_id: {"points": 0.0, "position": 0.0, "champion": 0, "top4": 0, "relegated": 0, "positions": defaultdict(int)} for team_id in teams}
    rng = random.Random(seed)
    for _ in range(max(1, simulations)):
        table = {team_id: values.copy() for team_id, values in base.items()}
        for fixture, forecast in forecasts:
            home, away = str(fixture["homeTeamId"]), str(fixture["awayTeamId"])
            home_goals = _sample_poisson(rng, forecast["expectedGoals"]["home"])
            away_goals = _sample_poisson(rng, forecast["expectedGoals"]["away"])
            table[home]["gf"] += home_goals
            table[home]["ga"] += away_goals
            table[away]["gf"] += away_goals
            table[away]["ga"] += home_goals
            if home_goals > away_goals:
                table[home]["points"] += 3
            elif home_goals == away_goals:
                table[home]["points"] += 1
                table[away]["points"] += 1
            else:
                table[away]["points"] += 3
        ordered = sorted(table, key=lambda team_id: (table[team_id]["points"], table[team_id]["gf"] - table[team_id]["ga"], table[team_id]["gf"]), reverse=True)
        for position, team_id in enumerate(ordered, 1):
            totals[team_id]["points"] += table[team_id]["points"]
            totals[team_id]["position"] += position
            totals[team_id]["positions"][position] += 1
            totals[team_id]["champion"] += position == 1
            totals[team_id]["top4"] += position <= 4
            totals[team_id]["relegated"] += position > len(teams) - 3
    result = []
    count = max(1, simulations)
    for team_id, aggregate in totals.items():
        position_counts = aggregate["positions"]
        position_distribution = {str(position): round(position_counts.get(position, 0) / count, 4) for position in range(1, len(teams) + 1)}
        ordered_positions = [position for position in range(1, len(teams) + 1) for _ in range(position_counts.get(position, 0))]
        low = ordered_positions[max(0, int(len(ordered_positions) * 0.1) - 1)] if ordered_positions else None
        high = ordered_positions[min(len(ordered_positions) - 1, int(len(ordered_positions) * 0.9))] if ordered_positions else None
        likely_position = min(position_counts, key=lambda position: (-position_counts[position], position), default=None)
        result.append({
            "team": teams[team_id],
            "expectedPoints": round(aggregate["points"] / count, 1),
            "expectedPosition": round(aggregate["position"] / count, 2),
            "likelyPosition": likely_position,
            "centralFinishingRange": {"low": low, "high": high, "method": "10th-90th percentile"},
            "positionDistribution": position_distribution,
            "championProbability": round(aggregate["champion"] / count, 4),
            "topFourProbability": round(aggregate["top4"] / count, 4),
            "relegationProbability": round(aggregate["relegated"] / count, 4),
        })
    return sorted(result, key=lambda row: row["expectedPosition"])

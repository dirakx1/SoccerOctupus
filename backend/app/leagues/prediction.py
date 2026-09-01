from __future__ import annotations

import math
import json
import random
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Iterable


MODEL_VERSION = "league-dixon-coles-2026.2"
ONLINE_MODEL_VERSION = "league-online-poisson-2026.1"
FOTMOB_ADJUSTMENT_VERSION = "fotmob-admission-2026.2"
RATING_HALF_LIFE_DAYS = 240.0
RATING_RIDGE = 0.02
FORM_COEFFICIENT = 0.0
REST_COEFFICIENT = 0.0
PROMOTION_STRENGTH_TRANSFER = 0.35
PROMOTED_ATTACK_CEILING = 0.0
PROMOTED_WEAKNESS_FLOOR = 0.0
ADMITTED_CORE_MODELS = {
    "premier-league": "dixon-coles",
    "la-liga": "dixon-coles",
    "bundesliga": "online-poisson",
}


def league_model_version(competition: str | None) -> str:
    return ONLINE_MODEL_VERSION if ADMITTED_CORE_MODELS.get(competition) == "online-poisson" else MODEL_VERSION


def admitted_fotmob_records(season) -> tuple[dict[str, Any], ...]:
    """Load only the compact historical cache after a persisted gate pass."""
    root = season.directory.parent.parent
    report_path = root / f"fotmob-admission-{season.competition}.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    if report.get("version") != FOTMOB_ADJUSTMENT_VERSION or report.get("adjustmentsApplied") is not True:
        return ()
    records: list[dict[str, Any]] = []
    for season_name in ("2024-25", "2025-26"):
        try:
            audit = json.loads((root / season.competition / season_name / "fotmob.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        records.extend(item for item in audit.get("fixtures", ()) if item.get("stats"))
    return tuple(records)


def _poisson(lam: float, goals: int) -> float:
    return math.exp(-lam) * lam**goals / math.factorial(goals)


def _dixon_coles_factor(home_goals: int, away_goals: int, home_xg: float, away_xg: float, rho: float) -> float:
    if home_goals == 0 and away_goals == 0:
        return 1 - home_xg * away_xg * rho
    if home_goals == 0 and away_goals == 1:
        return 1 + home_xg * rho
    if home_goals == 1 and away_goals == 0:
        return 1 + away_xg * rho
    if home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


def _outcomes(home_xg: float, away_xg: float, rho: float = 0.0) -> tuple[dict[str, float], tuple[int, int], float, float]:
    home = draw = away = btts = over25 = 0.0
    best = (0, 0)
    best_probability = -1.0
    for home_goals in range(9):
        for away_goals in range(9):
            probability = _poisson(home_xg, home_goals) * _poisson(away_xg, away_goals)
            probability *= max(0.0, _dixon_coles_factor(home_goals, away_goals, home_xg, away_xg, rho))
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
    return ({"home": home / total, "draw": draw / total, "away": away / total}, best, btts / total, over25 / total)


def _score_probabilities(home_xg: float, away_xg: float, rho: float = 0.0, *, limit: int = 9) -> list[dict[str, Any]]:
    """Return the ordered scoreline distribution used by the outcome model."""
    rows = []
    total = 0.0
    for home_goals in range(limit):
        for away_goals in range(limit):
            probability = _poisson(home_xg, home_goals) * _poisson(away_xg, away_goals)
            probability *= max(0.0, _dixon_coles_factor(home_goals, away_goals, home_xg, away_xg, rho))
            total += probability
            rows.append((probability, home_goals, away_goals))
    return [
        {"score": f"{home_goals}-{away_goals}", "home": home_goals, "away": away_goals, "probability": probability / total}
        for probability, home_goals, away_goals in sorted(rows, reverse=True)[:5]
    ]


class LeaguePredictionModel:
    """Leakage-safe league models using only information available before kickoff."""

    def __init__(
        self,
        *,
        teams: Iterable[dict[str, Any]],
        completed_fixtures: Iterable[dict[str, Any]],
        promoted_team_ids: set[str] | None = None,
        fotmob_records: Iterable[dict[str, Any]] = (),
        competition: str | None = None,
    ):
        self.teams = {str(team["id"]): team for team in teams}
        self.completed = sorted(completed_fixtures, key=lambda item: item["kickoff"])
        self.promoted = promoted_team_ids or set()
        self.fotmob_records = tuple(fotmob_records)
        self.competition = competition
        self._fit_cache: dict[int, tuple[float, float, dict[str, float], dict[str, float], float]] = {}

    def _training_rows(self, before: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        top_flight = []
        lower_division = []
        for fixture in self.completed:
            kickoff = datetime.fromisoformat(fixture["kickoff"].replace("Z", "+00:00"))
            if kickoff >= before:
                continue
            source = fixture.get("_competition")
            if self.competition and source and source != self.competition:
                lower_division.append(fixture)
            else:
                top_flight.append(fixture)
        return top_flight, lower_division

    def _promoted_priors(self, fixtures: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, float]]:
        attack_prior = {team_id: -0.12 for team_id in self.promoted}
        weakness_prior = {team_id: 0.08 for team_id in self.promoted}
        if not fixtures:
            return attack_prior, weakness_prior
        league_goals = sum(int(row["homeScore"]) + int(row["awayScore"]) for row in fixtures)
        league_games = 2 * len(fixtures)
        if league_goals <= 0 or league_games <= 0:
            return attack_prior, weakness_prior
        league_rate = league_goals / league_games
        for team_id in self.promoted:
            goals_for = goals_against = matches = 0
            for row in fixtures:
                home, away = str(row["homeTeamId"]), str(row["awayTeamId"])
                if team_id == home:
                    goals_for += int(row["homeScore"])
                    goals_against += int(row["awayScore"])
                    matches += 1
                elif team_id == away:
                    goals_for += int(row["awayScore"])
                    goals_against += int(row["homeScore"])
                    matches += 1
            if matches >= 10:
                scored = max(0.25, goals_for / matches)
                conceded = max(0.25, goals_against / matches)
                # Retain only part of lower-division relative strength, then
                # apply a conservative step-up penalty. Top-flight results
                # increasingly replace this prior through the fitted ratings.
                attack_prior[team_id] = min(PROMOTED_ATTACK_CEILING, max(-0.35, PROMOTION_STRENGTH_TRANSFER * math.log(scored / league_rate) - 0.12))
                weakness_prior[team_id] = min(0.30, max(PROMOTED_WEAKNESS_FLOOR, PROMOTION_STRENGTH_TRANSFER * math.log(conceded / league_rate) + 0.08))
        return attack_prior, weakness_prior

    def _fit(self, before: datetime) -> tuple[float, float, dict[str, float], dict[str, float], float]:
        fixtures, lower_division = self._training_rows(before)
        cache_key = len(fixtures)
        cached = self._fit_cache.get(cache_key)
        if cached is not None:
            return cached
        if not fixtures:
            attack_prior, weakness_prior = self._promoted_priors(lower_division)
            result = (1.45, 1.15, attack_prior, weakness_prior, 0.0)
            self._fit_cache[cache_key] = result
            return result

        latest = max(datetime.fromisoformat(row["kickoff"].replace("Z", "+00:00")) for row in fixtures)
        weighted = []
        home_goals = away_goals = total_weight = 0.0
        team_ids = set(self.teams)
        for row in fixtures:
            kickoff = datetime.fromisoformat(row["kickoff"].replace("Z", "+00:00"))
            weight = 0.5 ** (max(0.0, (latest - kickoff).total_seconds() / 86400) / RATING_HALF_LIFE_DAYS)
            home_score, away_score = int(row["homeScore"]), int(row["awayScore"])
            home, away = str(row["homeTeamId"]), str(row["awayTeamId"])
            weighted.append((home, away, home_score, away_score, weight))
            team_ids.update((home, away))
            home_goals += weight * home_score
            away_goals += weight * away_score
            total_weight += weight

        log_home = math.log(max(0.4, home_goals / total_weight))
        log_away = math.log(max(0.4, away_goals / total_weight))
        promoted_attack, promoted_weakness = self._promoted_priors(lower_division)
        attack = {team_id: promoted_attack.get(team_id, 0.0) for team_id in team_ids}
        weakness = {team_id: promoted_weakness.get(team_id, 0.0) for team_id in team_ids}
        attack_m = defaultdict(float)
        attack_v = defaultdict(float)
        weakness_m = defaultdict(float)
        weakness_v = defaultdict(float)
        beta1, beta2, learning_rate = 0.9, 0.999, 0.045

        for iteration in range(1, 121):
            grad_attack = defaultdict(float)
            grad_weakness = defaultdict(float)
            for home, away, home_score, away_score, weight in weighted:
                expected_home = min(5.0, math.exp(log_home + attack[home] + weakness[away]))
                expected_away = min(5.0, math.exp(log_away + attack[away] + weakness[home]))
                home_error = weight * (expected_home - home_score) / total_weight
                away_error = weight * (expected_away - away_score) / total_weight
                grad_attack[home] += home_error
                grad_weakness[away] += home_error
                grad_attack[away] += away_error
                grad_weakness[home] += away_error
            for team_id in team_ids:
                attack_target = promoted_attack.get(team_id, 0.0)
                weakness_target = promoted_weakness.get(team_id, 0.0)
                for values, moments, squares, gradient in (
                    (attack, attack_m, attack_v, grad_attack[team_id] + RATING_RIDGE * (attack[team_id] - attack_target)),
                    (weakness, weakness_m, weakness_v, grad_weakness[team_id] + RATING_RIDGE * (weakness[team_id] - weakness_target)),
                ):
                    moments[team_id] = beta1 * moments[team_id] + (1 - beta1) * gradient
                    squares[team_id] = beta2 * squares[team_id] + (1 - beta2) * gradient * gradient
                    corrected_m = moments[team_id] / (1 - beta1**iteration)
                    corrected_v = squares[team_id] / (1 - beta2**iteration)
                    values[team_id] -= learning_rate * corrected_m / (math.sqrt(corrected_v) + 1e-8)
            attack_mean = sum(attack.values()) / len(attack)
            weakness_mean = sum(weakness.values()) / len(weakness)
            for team_id in team_ids:
                attack[team_id] -= attack_mean
                weakness[team_id] -= weakness_mean

        rho = 0.0
        best_likelihood = float("-inf")
        for candidate in (value / 100 for value in range(-15, 16)):
            likelihood = 0.0
            valid = True
            for home, away, home_score, away_score, weight in weighted:
                if home_score > 1 or away_score > 1:
                    continue
                expected_home = math.exp(log_home + attack[home] + weakness[away])
                expected_away = math.exp(log_away + attack[away] + weakness[home])
                factor = _dixon_coles_factor(home_score, away_score, expected_home, expected_away, candidate)
                if factor <= 0:
                    valid = False
                    break
                likelihood += weight * math.log(factor)
            if valid and likelihood > best_likelihood:
                best_likelihood = likelihood
                rho = candidate
        result = (math.exp(log_home), math.exp(log_away), attack, weakness, rho)
        self._fit_cache[cache_key] = result
        return result

    def _recent_context(self, before: datetime) -> tuple[dict[str, deque[int]], dict[str, datetime]]:
        form: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=5))
        last_match: dict[str, datetime] = {}
        for fixture in self.completed:
            kickoff = datetime.fromisoformat(fixture["kickoff"].replace("Z", "+00:00"))
            if kickoff >= before:
                continue
            source = fixture.get("_competition")
            if self.competition and source and source != self.competition:
                continue
            home, away = str(fixture["homeTeamId"]), str(fixture["awayTeamId"])
            home_score, away_score = int(fixture["homeScore"]), int(fixture["awayScore"])
            if home_score > away_score:
                points = (3, 0)
            elif home_score < away_score:
                points = (0, 3)
            else:
                points = (1, 1)
            form[home].append(points[0])
            form[away].append(points[1])
            last_match[home] = kickoff
            last_match[away] = kickoff
        return form, last_match

    def _online_ratings(self, before: datetime) -> tuple[dict[str, float], dict[str, float]]:
        """Previously admitted online baseline retained where fitted ratings regress."""
        attack = defaultdict(float)
        defence = defaultdict(float)
        for team_id in self.promoted:
            attack[team_id] = -0.12
            defence[team_id] = -0.08
        for fixture in self.completed:
            kickoff = datetime.fromisoformat(fixture["kickoff"].replace("Z", "+00:00"))
            if kickoff >= before:
                continue
            source = fixture.get("_competition")
            if self.competition and source and source != self.competition:
                continue
            home, away = str(fixture["homeTeamId"]), str(fixture["awayTeamId"])
            home_score, away_score = int(fixture["homeScore"]), int(fixture["awayScore"])
            expected_home = 1.45 * math.exp(attack[home] - defence[away])
            expected_away = 1.15 * math.exp(attack[away] - defence[home])
            home_error, away_error = home_score - expected_home, away_score - expected_away
            attack[home] += 0.035 * home_error
            defence[away] -= 0.035 * home_error
            attack[away] += 0.035 * away_error
            defence[home] -= 0.035 * away_error
        return attack, defence

    def rating_uncertainty(self, before: datetime) -> dict[str, float]:
        """Approximate log-strength uncertainty from recency-weighted match information."""
        fixtures, _ = self._training_rows(before)
        if not fixtures:
            return {team_id: 0.24 for team_id in self.teams}
        latest = max(datetime.fromisoformat(row["kickoff"].replace("Z", "+00:00")) for row in fixtures)
        information = defaultdict(float)
        for row in fixtures:
            kickoff = datetime.fromisoformat(row["kickoff"].replace("Z", "+00:00"))
            weight = 0.5 ** (max(0.0, (latest - kickoff).total_seconds() / 86400) / RATING_HALF_LIFE_DAYS)
            information[str(row["homeTeamId"])] += weight
            information[str(row["awayTeamId"])] += weight
        return {
            team_id: min(0.24, max(0.07, 0.55 / math.sqrt(4 + information[team_id]) + (0.025 if team_id in self.promoted else 0.0)))
            for team_id in self.teams
        }

    def predict(self, home_team_id: str, away_team_id: str, *, kickoff: datetime) -> dict[str, Any]:
        home, away = str(home_team_id), str(away_team_id)
        if home not in self.teams or away not in self.teams or home == away:
            raise ValueError("prediction requires two different registered teams")
        form, last_match = self._recent_context(kickoff)
        home_form = sum(form[home]) / max(1, len(form[home]))
        away_form = sum(form[away]) / max(1, len(form[away]))
        form_delta = (home_form - away_form) / 3
        core_model = ADMITTED_CORE_MODELS.get(self.competition, "dixon-coles")
        form_is_numeric = core_model == "online-poisson"
        if core_model == "online-poisson":
            attack, defence = self._online_ratings(kickoff)
            base_home, base_away, rho = 1.45, 1.15, 0.0
            home_strength = attack[home] - defence[away] + 0.08 * form_delta
            away_strength = attack[away] - defence[home] - 0.08 * form_delta
        else:
            base_home, base_away, attack, weakness, rho = self._fit(kickoff)
            home_strength = attack.get(home, 0.0) + weakness.get(away, 0.0) + FORM_COEFFICIENT * form_delta
            away_strength = attack.get(away, 0.0) + weakness.get(home, 0.0) - FORM_COEFFICIENT * form_delta
        home_rest = min(14.0, max(3.0, (kickoff - last_match[home]).total_seconds() / 86400)) if home in last_match else 7.0
        away_rest = min(14.0, max(3.0, (kickoff - last_match[away]).total_seconds() / 86400)) if away in last_match else 7.0
        rest_delta = (home_rest - away_rest) / 7
        home_xg = min(4.0, max(0.2, base_home * math.exp(home_strength + REST_COEFFICIENT * rest_delta)))
        away_xg = min(4.0, max(0.2, base_away * math.exp(away_strength - REST_COEFFICIENT * rest_delta)))
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
        probabilities, score, btts, over25 = _outcomes(home_xg, away_xg, rho)
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
                "reason": f"Recent form points are {home_points} to {away_points} across available completed matches. " + ("This contributes to the forecast." if form_is_numeric else "Backtesting did not support an additional form adjustment, so this is explanatory only."),
                "sources": ["ESPN completed results"],
            },
            {
                "name": "Home advantage",
                "direction": "home",
                "reason": "The baseline uses the league's fitted home and away scoring environment." if core_model == "dixon-coles" else "The admitted online baseline applies its fixed home-venue scoring advantage.",
                "sources": ["league Poisson baseline"],
            },
            {
                "name": "Rest and congestion",
                "direction": "home" if home_rest > away_rest else "away" if away_rest > home_rest else "neutral",
                "reason": f"Rest before kickoff is {home_rest:.0f} days for {self.teams[home]['name']} and {away_rest:.0f} days for {self.teams[away]['name']}. Backtesting did not support a numerical rest adjustment.",
                "sources": ["ESPN fixture chronology"],
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
            {"name": "Recent form", "status": "active" if form_is_numeric else "evidence-only", "numericContribution": form_is_numeric, "sources": ["ESPN completed results"], "reason": "Uses each club's available pre-kickoff five-match points." if form_is_numeric else "Displayed as context; the fitted model's validated form coefficient is zero."},
            {"name": "Tactical", "status": "unavailable", "numericContribution": False, "sources": [], "reason": "No verified fixture-bound tactical dataset is available for this league snapshot."},
            {"name": "Squad quality", "status": "unavailable", "numericContribution": False, "sources": [], "reason": "No verified pre-kickoff squad availability and player-rating snapshot is available."},
            {"name": "Live data", "status": "evidence-only", "numericContribution": False, "sources": ["FotMob admission gate"], "reason": "Admitted FotMob xG/shots can adjust the baseline only after the persisted gate passes."},
            {"name": "Market signals", "status": "unavailable", "numericContribution": False, "sources": [], "reason": "No league market feed has passed the numerical admission gate."},
            {"name": "Video intelligence", "status": "unavailable", "numericContribution": False, "sources": [], "reason": "Video analysis is not verified as a pre-kickoff league input."},
        ]
        favored_name = self.teams[home]["name"] if outcome == "home" else self.teams[away]["name"] if outcome == "away" else "draw"
        return {
            "modelVersion": league_model_version(self.competition),
            "generatedAt": datetime.now(kickoff.tzinfo).isoformat(),
            "homeTeam": self.teams[home],
            "awayTeam": self.teams[away],
            "outcome": {"home": "home_win", "draw": "draw", "away": "away_win"}[outcome],
            "probabilities": probabilities,
            "expectedGoals": {"home": round(home_xg, 3), "away": round(away_xg, 3)},
            "likelyScore": {"home": score[0], "away": score[1]},
            "scoreProbabilities": _score_probabilities(home_xg, away_xg, rho),
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
                "inputs": (["ESPN completed results", "online attack and defence", "five-match form", "promoted-team prior"] if core_model == "online-poisson" else ["ESPN completed results", "time-decayed fitted attack and defence", "league scoring environment", "Dixon-Coles low-score correction", "translated promoted-team prior"]) + (["rest and congestion"] if REST_COEFFICIENT else []) + (["FotMob rolling xG/shots"] if adjustment_applied else []),
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


def _mini_table(team_ids: list[str], head_to_head: dict[tuple[str, str], dict[str, dict[str, int]]]) -> dict[str, tuple[int, int, int, int]]:
    totals = {team_id: {"points": 0, "gf": 0, "ga": 0, "awayGoals": 0} for team_id in team_ids}
    selected = set(team_ids)
    for pair, values in head_to_head.items():
        if set(pair) <= selected:
            for team_id, row in values.items():
                totals[team_id]["points"] += row["points"]
                totals[team_id]["gf"] += row["gf"]
                totals[team_id]["ga"] += row["ga"]
                totals[team_id]["awayGoals"] += row.get("awayGoals", 0)
    return {team_id: (row["points"], row["gf"] - row["ga"], row["gf"], row["awayGoals"]) for team_id, row in totals.items()}


def _order_table(table: dict[str, dict[str, int]], head_to_head: dict[tuple[str, str], dict[str, dict[str, int]]], competition: str) -> list[str]:
    if competition == "la-liga":
        groups: dict[int, list[str]] = defaultdict(list)
        for team_id, row in table.items():
            groups[row["points"]].append(team_id)
        ordered = []
        for points in sorted(groups, reverse=True):
            tied = groups[points]
            mini = _mini_table(tied, head_to_head)
            ordered.extend(sorted(tied, key=lambda team_id: (mini[team_id][:3], table[team_id]["gf"] - table[team_id]["ga"], table[team_id]["gf"], team_id), reverse=True))
        return ordered

    primary = lambda team_id: (table[team_id]["points"], table[team_id]["gf"] - table[team_id]["ga"], table[team_id]["gf"])
    prelim = sorted(table, key=primary, reverse=True)
    ordered = []
    start = 0
    while start < len(prelim):
        end = start + 1
        while end < len(prelim) and primary(prelim[end]) == primary(prelim[start]):
            end += 1
        tied = prelim[start:end]
        mini = _mini_table(tied, head_to_head)
        if competition == "bundesliga":
            # Aggregate head-to-head result, head-to-head away goals, then all
            # away goals. The final team ID is only a deterministic stand-in
            # for the practically unreachable neutral-playoff case.
            key = lambda team_id: (mini[team_id][1], mini[team_id][3], table[team_id].get("awayGoals", 0), team_id)
        else:
            # Premier League: head-to-head points, then away goals in those
            # matches, after overall points/GD/GF have already tied.
            key = lambda team_id: (mini[team_id][0], mini[team_id][3], team_id)
        ordered.extend(sorted(tied, key=key, reverse=True))
        start = end
    return ordered


def _record_head_to_head(head_to_head: dict[tuple[str, str], dict[str, dict[str, int]]], home: str, away: str, home_goals: int, away_goals: int) -> None:
    pair = tuple(sorted((home, away)))
    values = head_to_head.setdefault(pair, {home: {"points": 0, "gf": 0, "ga": 0, "awayGoals": 0}, away: {"points": 0, "gf": 0, "ga": 0, "awayGoals": 0}})
    values.setdefault(home, {"points": 0, "gf": 0, "ga": 0, "awayGoals": 0})
    values.setdefault(away, {"points": 0, "gf": 0, "ga": 0, "awayGoals": 0})
    values[home]["gf"] += home_goals
    values[home]["ga"] += away_goals
    values[away]["gf"] += away_goals
    values[away]["ga"] += home_goals
    values[away]["awayGoals"] += away_goals
    if home_goals > away_goals:
        values[home]["points"] += 3
    elif away_goals > home_goals:
        values[away]["points"] += 3
    else:
        values[home]["points"] += 1
        values[away]["points"] += 1


def project_table(season, *, simulations: int = 2000, seed: int = 20260829) -> list[dict[str, Any]]:
    teams = {str(team["id"]): team for team in season.teams}
    base = {team_id: {"points": 0, "gf": 0, "ga": 0, "awayGoals": 0} for team_id in teams}
    for row in season.standings:
        team_id = str(row["teamId"])
        base[team_id] = {"points": int(row["points"]), "gf": int(row["goalsFor"]), "ga": int(row["goalsAgainst"]), "awayGoals": 0}
    remaining = [fixture for fixture in season.fixtures if fixture["status"] == "scheduled"]
    model = LeaguePredictionModel(teams=season.teams, completed_fixtures=season.completed_fixtures, promoted_team_ids=season.promoted_team_ids, fotmob_records=admitted_fotmob_records(season), competition=season.competition)
    cutoff = max((datetime.fromisoformat(fixture["kickoff"].replace("Z", "+00:00")) for fixture in season.fixtures if fixture.get("status") == "completed"), default=datetime.fromisoformat(remaining[0]["kickoff"].replace("Z", "+00:00")) if remaining else datetime.now().astimezone())
    uncertainty = model.rating_uncertainty(cutoff)
    base_head_to_head: dict[tuple[str, str], dict[str, dict[str, int]]] = {}
    for fixture in season.fixtures:
        if fixture.get("status") == "completed":
            base[str(fixture["awayTeamId"])]["awayGoals"] += int(fixture["awayScore"])
            _record_head_to_head(base_head_to_head, str(fixture["homeTeamId"]), str(fixture["awayTeamId"]), int(fixture["homeScore"]), int(fixture["awayScore"]))
    forecasts = []
    for fixture in remaining:
        kickoff = datetime.fromisoformat(fixture["kickoff"].replace("Z", "+00:00"))
        forecasts.append((fixture, model.predict(fixture["homeTeamId"], fixture["awayTeamId"], kickoff=kickoff)))
    totals = {team_id: {"points": 0.0, "position": 0.0, "champion": 0, "top4": 0, "relegated": 0, "positions": defaultdict(int)} for team_id in teams}
    rng = random.Random(seed)
    for _ in range(max(1, simulations)):
        table = {team_id: values.copy() for team_id, values in base.items()}
        head_to_head = {pair: {team_id: row.copy() for team_id, row in values.items()} for pair, values in base_head_to_head.items()}
        attack_noise = {team_id: rng.gauss(-0.5 * uncertainty[team_id] ** 2, uncertainty[team_id]) for team_id in teams}
        defence_noise = {team_id: rng.gauss(-0.5 * uncertainty[team_id] ** 2, uncertainty[team_id]) for team_id in teams}
        for fixture, forecast in forecasts:
            home, away = str(fixture["homeTeamId"]), str(fixture["awayTeamId"])
            home_rate = forecast["expectedGoals"]["home"] * math.exp(attack_noise[home] + defence_noise[away])
            away_rate = forecast["expectedGoals"]["away"] * math.exp(attack_noise[away] + defence_noise[home])
            home_goals = _sample_poisson(rng, home_rate)
            away_goals = _sample_poisson(rng, away_rate)
            table[home]["gf"] += home_goals
            table[home]["ga"] += away_goals
            table[away]["gf"] += away_goals
            table[away]["ga"] += home_goals
            table[away]["awayGoals"] += away_goals
            if home_goals > away_goals:
                table[home]["points"] += 3
            elif home_goals == away_goals:
                table[home]["points"] += 1
                table[away]["points"] += 1
            else:
                table[away]["points"] += 3
            _record_head_to_head(head_to_head, home, away, home_goals, away_goals)
        ordered = _order_table(table, head_to_head, season.competition)
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

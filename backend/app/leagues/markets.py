"""League-only fair-value market questions.

These contracts use the canonical ESPN-backed league forecast and are not
bookmaker or exchange prices.  World Cup market generation remains separate.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Iterable

from ..models.market import MarketQuestion, Platform


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")


def _question(
    *,
    question_id: str,
    question: str,
    short_title: str,
    yes_probability: float,
    prop_type: str,
    home: str | None,
    away: str | None,
    resolution_date: str,
    criteria: str,
    confidence: float,
    season: str,
    subcategory: str,
    tags: list[str],
    resolution_source: str,
    fixture_id: str | None = None,
) -> dict[str, Any]:
    item = MarketQuestion(
        question_id=question_id,
        market_type="binary",
        question=question,
        short_title=short_title,
        subcategory=subcategory,
        tags=tags + ([str(fixture_id)] if fixture_id else []),
        yes_probability=max(0.0, min(1.0, float(yes_probability))),
        no_probability=max(0.0, min(1.0, 1.0 - float(yes_probability))),
        resolution_criteria=criteria,
        resolution_source=resolution_source,
        resolution_date=resolution_date,
        platforms=list(Platform.BOTH),
        confidence=confidence,
        related_teams=[name for name in (home, away) if name],
        stage="league",
        prop_type=prop_type,
    )
    return item.to_dict()


def _poisson(lam: float, goals: int) -> float:
    return math.exp(-lam) * lam**goals / math.factorial(goals)


def _over_probability(home_xg: float, away_xg: float, threshold: int) -> float:
    total = sum(_poisson(home_xg, home_goals) * _poisson(away_xg, away_goals) for home_goals in range(9) for away_goals in range(9))
    over = sum(_poisson(home_xg, home_goals) * _poisson(away_xg, away_goals) for home_goals in range(9) for away_goals in range(9) if home_goals + away_goals > threshold)
    return over / total


def match_questions(*, competition: str, season: str, fixture: dict[str, Any], forecast: dict[str, Any], home: str, away: str, competition_name: str | None = None, competition_tag: str | None = None) -> list[dict[str, Any]]:
    competition_name = competition_name or str(competition).replace("-", " ").title()
    competition_tag = competition_tag or _slug(competition)
    subcategory = f"Soccer – {competition_name} {season}"
    resolution_source = f"ESPN official {competition_name} match results"
    fixture_id = _slug(fixture["id"])
    kickoff = datetime.fromisoformat(str(fixture["kickoff"]).replace("Z", "+00:00"))
    resolution_date = kickoff.date().isoformat()
    prefix = f"{_slug(competition)}-{_slug(season)}-{fixture_id}"
    probabilities = forecast["probabilities"]
    markets = forecast["markets"]
    home_xg = float(forecast["expectedGoals"]["home"])
    away_xg = float(forecast["expectedGoals"]["away"])
    confidence = float(forecast.get("confidence", max(probabilities.values())))
    criteria = f"Resolved from the official ESPN {competition_name} result after 90 minutes."
    tags = [competition_tag, season]
    questions = [
        _question(question_id=f"{prefix}-home-win", question=f"Will {home} beat {away}?", short_title=f"{home} to win", yes_probability=probabilities["home"], prop_type="match_winner", home=home, away=away, resolution_date=resolution_date, criteria=criteria, confidence=confidence, season=season, subcategory=subcategory, tags=tags, resolution_source=resolution_source, fixture_id=fixture["id"]),
        _question(question_id=f"{prefix}-draw", question=f"Will {home} vs {away} end in a draw?", short_title="Match draw", yes_probability=probabilities["draw"], prop_type="draw", home=home, away=away, resolution_date=resolution_date, criteria=criteria, confidence=confidence, season=season, subcategory=subcategory, tags=tags, resolution_source=resolution_source, fixture_id=fixture["id"]),
        _question(question_id=f"{prefix}-away-win", question=f"Will {away} beat {home}?", short_title=f"{away} to win", yes_probability=probabilities["away"], prop_type="match_winner", home=home, away=away, resolution_date=resolution_date, criteria=criteria, confidence=confidence, season=season, subcategory=subcategory, tags=tags, resolution_source=resolution_source, fixture_id=fixture["id"]),
        _question(question_id=f"{prefix}-btts", question=f"Will {home} and {away} both score?", short_title="Both teams to score", yes_probability=markets["bothTeamsToScoreYes"], prop_type="btts", home=home, away=away, resolution_date=resolution_date, criteria=criteria, confidence=confidence, season=season, subcategory=subcategory, tags=tags, resolution_source=resolution_source, fixture_id=fixture["id"]),
    ]
    for threshold in (1.5, 2.5, 3.5):
        questions.append(_question(question_id=f"{prefix}-over-{str(threshold).replace('.', '-')}", question=f"Will {home} vs {away} have over {threshold} goals?", short_title=f"Over {threshold} goals", yes_probability=_over_probability(home_xg, away_xg, int(threshold)), prop_type="over_under", home=home, away=away, resolution_date=resolution_date, criteria=criteria, confidence=confidence, season=season, subcategory=subcategory, tags=tags, resolution_source=resolution_source, fixture_id=fixture["id"]))
    questions.extend([
        _question(question_id=f"{prefix}-home-clean-sheet", question=f"Will {home} keep a clean sheet?", short_title=f"{home} clean sheet", yes_probability=markets["homeCleanSheet"], prop_type="clean_sheet", home=home, away=away, resolution_date=resolution_date, criteria=criteria, confidence=confidence, season=season, subcategory=subcategory, tags=tags, resolution_source=resolution_source, fixture_id=fixture["id"]),
        _question(question_id=f"{prefix}-away-clean-sheet", question=f"Will {away} keep a clean sheet?", short_title=f"{away} clean sheet", yes_probability=markets["awayCleanSheet"], prop_type="clean_sheet", home=home, away=away, resolution_date=resolution_date, criteria=criteria, confidence=confidence, season=season, subcategory=subcategory, tags=tags, resolution_source=resolution_source, fixture_id=fixture["id"]),
    ])
    likely = (forecast.get("scoreProbabilities") or [{}])[0]
    likely_score = f"{likely.get('home', 0)}-{likely.get('away', 0)}"
    questions.append(_question(question_id=f"{prefix}-correct-score-{_slug(likely_score)}", question=f"Will {home} vs {away} finish {likely_score}?", short_title=f"Correct score {likely_score}", yes_probability=float(likely.get("probability", 0.0)), prop_type="correct_score", home=home, away=away, resolution_date=resolution_date, criteria=criteria, confidence=confidence, season=season, subcategory=subcategory, tags=tags, resolution_source=resolution_source, fixture_id=fixture["id"]))
    return questions


def season_questions(*, competition: str, season: str, end_date: str, projected: Iterable[dict[str, Any]], competition_name: str | None = None, competition_tag: str | None = None) -> list[dict[str, Any]]:
    competition_name = competition_name or str(competition).replace("-", " ").title()
    competition_tag = competition_tag or _slug(competition)
    subcategory = f"Soccer – {competition_name} {season}"
    resolution_source = f"ESPN official {competition_name} results"
    criteria = f"Resolved from the final official ESPN {season} {competition_name} table."
    questions = []
    for row in projected:
        team = row["team"]
        team_id = _slug(team["id"])
        name = team["name"]
        for key, label, prop_type in (("championProbability", f"win {competition_name}", "tournament_winner"), ("topFourProbability", "finish in the top four", "reach_stage"), ("relegationProbability", "be relegated", "futures")):
            questions.append(_question(question_id=f"{_slug(competition)}-{_slug(season)}-{team_id}-{_slug(prop_type)}", question=f"Will {name} {label} in {season}?", short_title=f"{name}: {label}", yes_probability=row[key], prop_type=prop_type, home=None, away=None, resolution_date=end_date, criteria=criteria, confidence=max(float(row[key]), 0.5), season=season, subcategory=subcategory, tags=[competition_tag, season], resolution_source=resolution_source, fixture_id=team["id"]))
    return questions

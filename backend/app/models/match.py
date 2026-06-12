"""
Domain models for matches, predictions, and tournament state.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


def _poisson_score(lam_home: float, lam_away: float, max_goals: int = 6) -> str:
    """Most likely scoreline by joint Poisson probability."""
    def pmf(lam: float, k: int) -> float:
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    best, bh, ba = -1.0, 0, 0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = pmf(lam_home, h) * pmf(lam_away, a)
            if p > best:
                best, bh, ba = p, h, a
    return f"{bh}-{ba}"


class MatchStage(str, Enum):
    GROUP = "group"
    ROUND_OF_32 = "round_of_32"
    ROUND_OF_16 = "round_of_16"
    QUARTER_FINAL = "quarter_final"
    SEMI_FINAL = "semi_final"
    THIRD_PLACE = "third_place"
    FINAL = "final"


class MatchOutcome(str, Enum):
    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"


@dataclass
class TeamProfile:
    """Static + dynamic profile for a national team."""
    name: str
    fifa_code: str          # e.g. "BRA", "ARG"
    elo_rating: float       # World Football Elo rating
    fifa_ranking: int
    confederation: str      # UEFA, CONMEBOL, CAF, AFC, CONCACAF, OFC
    avg_goals_scored: float     # per match, last 12 months
    avg_goals_conceded: float
    attack_rating: float        # 0–100
    defense_rating: float       # 0–100
    form_points: float          # pts from last 10 official matches (out of 30)
    key_players: List[str] = field(default_factory=list)
    playing_style: str = "balanced"   # e.g. "high-press", "counter-attack", "tiki-taka"

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "fifa_code": self.fifa_code,
            "elo_rating": self.elo_rating,
            "fifa_ranking": self.fifa_ranking,
            "confederation": self.confederation,
            "avg_goals_scored": self.avg_goals_scored,
            "avg_goals_conceded": self.avg_goals_conceded,
            "attack_rating": self.attack_rating,
            "defense_rating": self.defense_rating,
            "form_points": self.form_points,
            "playing_style": self.playing_style,
        }


@dataclass
class AgentPrediction:
    """Single-agent match prediction."""
    agent_name: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    predicted_home_goals: float
    predicted_away_goals: float
    confidence: float           # 0–1
    reasoning: str
    data_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "agent": self.agent_name,
            "home_win_prob": round(self.home_win_prob, 3),
            "draw_prob": round(self.draw_prob, 3),
            "away_win_prob": round(self.away_win_prob, 3),
            "predicted_score": _poisson_score(self.predicted_home_goals, self.predicted_away_goals),
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "data_sources": self.data_sources,
        }


@dataclass
class MatchPrediction:
    """Aggregated swarm prediction for a single match."""
    prediction_id: str
    home_team: str
    away_team: str
    stage: MatchStage
    group: Optional[str]

    # Aggregated probabilities (weighted average of all agents)
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    predicted_home_goals: float
    predicted_away_goals: float
    most_likely_score: str          # e.g. "2-1"
    outcome: MatchOutcome
    overall_confidence: float

    # Per-agent breakdown
    agent_predictions: List[AgentPrediction] = field(default_factory=list)
    swarm_consensus: str = ""       # LLM-synthesized narrative
    key_factors: List[str] = field(default_factory=list)

    # True only in knockout matches where the 90-min result was a draw,
    # resolved by extra time / penalty shootout. Always False in group stage.
    went_to_penalties: bool = False

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "prediction_id": self.prediction_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "stage": self.stage.value,
            "group": self.group,
            "home_win_prob": round(self.home_win_prob, 3),
            "draw_prob": round(self.draw_prob, 3),
            "away_win_prob": round(self.away_win_prob, 3),
            "predicted_home_goals": round(self.predicted_home_goals, 2),
            "predicted_away_goals": round(self.predicted_away_goals, 2),
            "most_likely_score": self.most_likely_score,
            "outcome": self.outcome.value,
            "went_to_penalties": self.went_to_penalties,
            "overall_confidence": round(self.overall_confidence, 3),
            "agent_predictions": [a.to_dict() for a in self.agent_predictions],
            "swarm_consensus": self.swarm_consensus,
            "key_factors": self.key_factors,
            "created_at": self.created_at,
        }


@dataclass
class GroupStanding:
    team: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    def to_dict(self) -> Dict:
        return {
            "team": self.team,
            "played": self.played,
            "won": self.won,
            "drawn": self.drawn,
            "lost": self.lost,
            "gf": self.goals_for,
            "ga": self.goals_against,
            "gd": self.goal_difference,
            "points": self.points,
        }


@dataclass
class TournamentResult:
    """Complete simulated tournament result."""
    simulation_id: str
    champion: str
    runner_up: str
    third_place: str
    fourth_place: str
    group_results: Dict[str, List[GroupStanding]]   # group_letter → standings
    knockout_matches: List[MatchPrediction]
    champion_probability: float
    total_matches_simulated: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "simulation_id": self.simulation_id,
            "champion": self.champion,
            "runner_up": self.runner_up,
            "third_place": self.third_place,
            "fourth_place": self.fourth_place,
            "group_results": {
                g: [s.to_dict() for s in standings]
                for g, standings in self.group_results.items()
            },
            "knockout_matches": [m.to_dict() for m in self.knockout_matches],
            "champion_probability": round(self.champion_probability, 3),
            "total_matches_simulated": self.total_matches_simulated,
            "created_at": self.created_at,
        }

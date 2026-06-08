"""
Markets API blueprint
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..models.match import MatchStage
from ..services.market_question_generator import MarketQuestionGenerator
from ..services.swarm_orchestrator import SwarmOrchestrator
from ..services.tournament_simulator import TournamentSimulator
from ..utils.logger import get_logger

logger = get_logger("fifaoctopus.api.markets")
bp = Blueprint("markets", __name__, url_prefix="/api/markets")

_gen = MarketQuestionGenerator()
_orc: SwarmOrchestrator | None = None


def _get_orc() -> SwarmOrchestrator:
    global _orc
    if _orc is None:
        _orc = SwarmOrchestrator()
    return _orc


# ── Match market questions ─────────────────────────────────────────────────

@bp.route("/match", methods=["POST"])
def match_markets():
    """
    POST /api/markets/match
    Body: { "home_team": "France", "away_team": "Argentina", "stage": "final" }
    Returns all prediction market questions for a single match.
    """
    data = request.get_json(force=True) or {}
    home  = data.get("home_team", "").strip()
    away  = data.get("away_team", "").strip()
    stage_str = data.get("stage", "group")
    platform  = data.get("platform", "both").lower()   # kalshi | polymarket | both

    if not home or not away:
        return jsonify({"error": "home_team and away_team are required"}), 400

    try:
        stage = MatchStage(stage_str)
    except ValueError:
        stage = MatchStage.GROUP

    try:
        pred = _get_orc().predict_match(home, away, stage=stage)
        questions = _gen.from_match(pred)

        if platform == "kalshi":
            payload = [q.to_kalshi_format() for q in questions]
        elif platform == "polymarket":
            payload = [q.to_polymarket_format() for q in questions]
        else:
            payload = [q.to_dict() for q in questions]

        return jsonify({
            "match": f"{home} vs {away}",
            "stage": stage_str,
            "prediction_summary": {
                "home_win_prob": pred.home_win_prob,
                "draw_prob": pred.draw_prob,
                "away_win_prob": pred.away_win_prob,
                "most_likely_score": pred.most_likely_score,
            },
            "total_questions": len(questions),
            "questions": payload,
        }), 200
    except Exception as exc:
        logger.error(f"Match markets failed: {exc}")
        return jsonify({"error": str(exc)}), 500


# ── Tournament market questions ────────────────────────────────────────────

@bp.route("/tournament", methods=["POST"])
def tournament_markets():
    """
    POST /api/markets/tournament
    Body: { "platform": "both" }
    Simulates the full tournament and generates futures + group markets.
    """
    data = request.get_json(force=True) or {}
    platform = data.get("platform", "both").lower()

    try:
        sim = TournamentSimulator(orchestrator=None, use_swarm=False)
        result = sim.simulate()
        questions = _gen.from_tournament(result)

        if platform == "kalshi":
            payload = [q.to_kalshi_format() for q in questions]
        elif platform == "polymarket":
            payload = [q.to_polymarket_format() for q in questions]
        else:
            payload = [q.to_dict() for q in questions]

        # Group by prop_type for easier frontend rendering
        by_type: dict = {}
        for q in questions:
            t = q.prop_type
            by_type.setdefault(t, []).append(q.to_dict())

        return jsonify({
            "simulation": {
                "champion": result.champion,
                "runner_up": result.runner_up,
                "third_place": result.third_place,
                "champion_probability": result.champion_probability,
            },
            "total_questions": len(questions),
            "by_type": by_type,
            "questions": payload,
        }), 200
    except Exception as exc:
        logger.error(f"Tournament markets failed: {exc}")
        return jsonify({"error": str(exc)}), 500


# ── Filter by prop type ────────────────────────────────────────────────────

@bp.route("/types", methods=["GET"])
def market_types():
    return jsonify({
        "match_level": [
            "match_winner", "draw", "btts",
            "over_under", "clean_sheet", "penalties", "correct_score",
        ],
        "tournament_level": [
            "tournament_winner", "reach_stage",
            "group_winner", "confederation_win", "host_nation",
        ],
        "platforms": ["Kalshi", "Polymarket"],
        "resolution_source": "FIFA official match results (fifa.com)",
    })

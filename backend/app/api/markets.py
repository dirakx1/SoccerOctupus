"""
Markets API blueprint
"""

from __future__ import annotations

from flask import Blueprint, jsonify, g, request

from ..auth import require_user
from ..billing import includes_video_analysis
from ..db.base import db
from ..feature_limits import (
    FEATURE_MATCH_MARKET,
    FEATURE_TOURNAMENT_MARKET,
    release_feature_usage,
    reserve_feature_usage,
)
from ..models.match import MatchStage
from ..runtime_settings import RuntimeSettingsService
from ..services.market_question_generator import MarketQuestionGenerator
from ..services.swarm_orchestrator import SwarmOrchestrator
from ..services.tournament_simulator import TournamentSimulator
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger("fifaoctopus.api.markets")
bp = Blueprint("markets", __name__, url_prefix="/api/markets")

_gen = MarketQuestionGenerator()


def _get_orc(include_video_analysis: bool = True) -> SwarmOrchestrator:
    settings = RuntimeSettingsService.current(db)
    llm = None
    if settings.llm_api_key:
        llm = LLMClient(settings=settings)
    return SwarmOrchestrator(settings=settings, llm_client=llm, include_video_analysis=include_video_analysis)


# ── Match market questions ─────────────────────────────────────────────────

@bp.route("/match", methods=["POST"])
@require_user(db)
def match_markets():
    """
    POST /api/markets/match
    Body: { "home_team": "France", "away_team": "Argentina", "stage": "final" }
    Returns all prediction market questions for a single match.
    """
    data = request.get_json(silent=True) or {}
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

    reservation = reserve_feature_usage(g.current_user, FEATURE_MATCH_MARKET, db)
    if not reservation.allowed:
        return reservation.response

    try:
        pred = _get_orc(include_video_analysis=includes_video_analysis(g.current_user)).predict_match(home, away, stage=stage)
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
        release_feature_usage(reservation.cycle_limit_id, db)
        logger.error(f"Match markets failed: {exc}")
        return jsonify({"error": str(exc)}), 500


# ── Tournament market questions ────────────────────────────────────────────

@bp.route("/tournament", methods=["POST"])
@require_user(db)
def tournament_markets():
    """
    POST /api/markets/tournament
    Body: { "platform": "both" }
    Simulates the full tournament and generates futures + group markets.
    """
    data = request.get_json(silent=True) or {}
    platform = data.get("platform", "both").lower()
    reservation = reserve_feature_usage(g.current_user, FEATURE_TOURNAMENT_MARKET, db)
    if not reservation.allowed:
        return reservation.response

    try:
        settings = RuntimeSettingsService.current(db)
        sim = TournamentSimulator(
            orchestrator=None,
            use_swarm=False,
            mc_simulations=settings.mc_simulations,
        )
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
        release_feature_usage(reservation.cycle_limit_id, db)
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

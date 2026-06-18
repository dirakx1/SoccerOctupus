"""
Predictions API blueprint
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from flask import Blueprint, jsonify, g, request

from ..auth import require_admin, require_user
from ..config import Config
from ..db.base import db
from ..models.match import MatchStage
from ..runtime_settings import RuntimeSettingsService
from ..services.swarm_orchestrator import SwarmOrchestrator
from ..services.tournament_simulator import TournamentSimulator
from ..utils.logger import get_logger

logger = get_logger("fifaoctopus.api.predictions")
bp = Blueprint("predictions", __name__, url_prefix="/api/predictions")

def _get_orchestrator() -> SwarmOrchestrator:
    settings = RuntimeSettingsService.current(db)
    llm = None
    if settings.llm_api_key:
        from ..utils.llm_client import LLMClient

        llm = LLMClient(settings=settings)
    return SwarmOrchestrator(settings=settings, llm_client=llm)


# ------------------------------------------------------------------
# Single-match prediction
# ------------------------------------------------------------------

@bp.route("/match", methods=["POST"])
@require_user(db)
def predict_match():
    """
    POST /api/predictions/match
    Body: { "home_team": "...", "away_team": "...", "stage": "group", "group": "A" }
    """
    data: Dict[str, Any] = request.get_json(force=True) or {}
    home = data.get("home_team", "").strip()
    away = data.get("away_team", "").strip()
    stage_str = data.get("stage", "group")
    group = data.get("group")

    if not home or not away:
        return jsonify({"error": "home_team and away_team are required"}), 400

    try:
        stage = MatchStage(stage_str)
    except ValueError:
        stage = MatchStage.GROUP

    try:
        orc = _get_orchestrator()
        result = orc.predict_match(home, away, stage=stage, group=group)
        return jsonify(result.to_dict()), 200
    except Exception as exc:
        logger.error(f"Match prediction failed: {exc}")
        return jsonify({"error": str(exc)}), 500


# ------------------------------------------------------------------
# Full tournament simulation
# ------------------------------------------------------------------

@bp.route("/tournament", methods=["POST"])
@require_user(db)
def simulate_tournament():
    """
    POST /api/predictions/tournament
    Body: { "use_swarm": true }
    Returns the full WC2026 simulated bracket.
    """
    data = request.get_json(force=True) or {}
    use_swarm = data.get("use_swarm", False)   # default off — swarm is slow for 104 matches

    orc = _get_orchestrator() if use_swarm else None
    settings = RuntimeSettingsService.current(db)
    simulator = TournamentSimulator(
        orchestrator=orc,
        use_swarm=use_swarm,
        mc_simulations=settings.mc_simulations,
    )

    try:
        result = simulator.simulate()
        # Persist result
        _save_result(result.simulation_id, result.to_dict())
        return jsonify(result.to_dict()), 200
    except Exception as exc:
        logger.error(f"Tournament simulation failed: {exc}")
        return jsonify({"error": str(exc)}), 500


@bp.route("/tournament/<sim_id>", methods=["GET"])
@require_user(db)
def get_tournament_result(sim_id: str):
    path = os.path.join(Config.PREDICTIONS_DIR, f"{sim_id}.json")
    if not os.path.exists(path):
        return jsonify({"error": "not found"}), 404
    with open(path) as f:
        return jsonify(json.load(f)), 200


# ------------------------------------------------------------------
# Zep knowledge graph — build / status
# ------------------------------------------------------------------

@bp.route("/graph/build", methods=["POST"])
@require_admin(db)
def build_graph():
    """
    POST /api/predictions/graph/build
    Builds (or rebuilds) the Zep WC2026 knowledge graph.
    Mirrors MiroFish's /api/graph/build endpoint.
    Requires a Zep API key in admin settings.
    """
    settings = RuntimeSettingsService.current(db)
    if not settings.zep_api_key:
        return jsonify({"error": "Zep API key is not configured"}), 400

    progress_log = []

    def _cb(pct: int, msg: str):
        progress_log.append({"pct": pct, "msg": msg})

    try:
        from ..services.zep_football_graph import ZepFootballGraphBuilder
        builder = ZepFootballGraphBuilder(api_key=settings.zep_api_key)
        graph_id = builder.build(progress_callback=_cb)
        return jsonify({"graph_id": graph_id, "progress": progress_log}), 200
    except Exception as exc:
        logger.error(f"Graph build failed: {exc}")
        return jsonify({"error": str(exc)}), 500


@bp.route("/graph/status", methods=["GET"])
@require_admin(db)
def graph_status():
    """GET /api/predictions/graph/status — reports whether Zep is active."""
    from ..services.zep_football_tools import ZepFootballTools
    settings = RuntimeSettingsService.current(db)
    tools = ZepFootballTools(api_key=settings.zep_api_key, graph_id=settings.zep_graph_id)
    return jsonify({
        "zep_configured": bool(settings.zep_api_key),
        "graph_id": settings.zep_graph_id or None,
        "graph_active": tools.has_graph,
        "mode": "zep_graph" if tools.has_graph else "static_data_fallback",
    }), 200


# ------------------------------------------------------------------
# List available teams
# ------------------------------------------------------------------

@bp.route("/teams", methods=["GET"])
@require_user(db)
def list_teams():
    from ..services.data_collectors.sofascore_collector import TEAM_STATIC_DATA
    teams = [
        {"name": name, "elo": d["elo"], "rank": d["rank"], "style": d.get("style", "balanced")}
        for name, d in sorted(TEAM_STATIC_DATA.items(), key=lambda x: -x[1]["elo"])
    ]
    return jsonify({"teams": teams, "count": len(teams)}), 200


# ------------------------------------------------------------------
# World Cup 2026 groups
# ------------------------------------------------------------------

@bp.route("/groups", methods=["GET"])
@require_user(db)
def get_groups():
    from ..services.tournament_simulator import WC2026_GROUPS
    from ..services.data_collectors.sofascore_collector import TEAM_STATIC_DATA
    enriched = {}
    for g, teams in WC2026_GROUPS.items():
        enriched[g] = [
            {
                "team": t,
                "elo": TEAM_STATIC_DATA.get(t, {}).get("elo", 1800),
                "rank": TEAM_STATIC_DATA.get(t, {}).get("rank", 999),
            }
            for t in teams
        ]
    return jsonify({"groups": enriched}), 200


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _save_result(sim_id: str, data: Dict):
    os.makedirs(Config.PREDICTIONS_DIR, exist_ok=True)
    path = os.path.join(Config.PREDICTIONS_DIR, f"{sim_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

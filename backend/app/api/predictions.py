"""
Predictions API blueprint
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from flask import Blueprint, jsonify, g, request

from ..auth import require_admin, require_user
from ..billing import includes_video_analysis
from ..config import Config
from ..db.base import db
from ..feature_limits import (
    FEATURE_MATCH_PREDICTION,
    FEATURE_TOURNAMENT_SIMULATION,
    release_feature_usage,
    reserve_feature_usage,
)
from ..models.match import MatchOutcome, MatchStage
from ..runtime_settings import RuntimeSettingsService
from ..services.swarm_orchestrator import SwarmOrchestrator
from ..services.tournament_simulator import TournamentSimulator
from ..utils.logger import get_logger

logger = get_logger("fifaoctopus.api.predictions")
bp = Blueprint("predictions", __name__, url_prefix="/api/predictions")

def _get_orchestrator(
    include_video_analysis: bool = True,
    agent_weights: Dict[str, float] | None = None,
) -> SwarmOrchestrator:
    settings = RuntimeSettingsService.current(db)
    llm = None
    if settings.llm_api_key:
        from ..utils.llm_client import LLMClient

        llm = LLMClient(settings=settings)
    return SwarmOrchestrator(
        settings=settings,
        llm_client=llm,
        include_video_analysis=include_video_analysis,
        agent_weights=agent_weights,
    )


def _saved_weight_overrides(user) -> Dict[str, float]:
    """The user's persisted sparse weight overrides ({} when none)."""
    from ..db.models import UserSwarmPreference

    pref = db.session.get(UserSwarmPreference, user.id)
    return dict(pref.weights or {}) if pref else {}


def _effective_weight_overrides(user, body: Dict[str, Any]) -> Dict[str, float]:
    """
    Saved overrides, optionally superseded per-request by an `agent_weights`
    object in the request body (session-only experimentation).
    Raises ValueError on malformed request weights.
    """
    from ..services.agents.weights import validate_overrides

    overrides = _saved_weight_overrides(user)
    if isinstance(body.get("agent_weights"), dict):
        overrides.update(validate_overrides(body["agent_weights"]))
    return overrides


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

    reservation = reserve_feature_usage(g.current_user, FEATURE_MATCH_PREDICTION, db)
    if not reservation.allowed:
        return reservation.response

    try:
        import random as _random
        try:
            weights = _effective_weight_overrides(g.current_user, data)
        except ValueError as exc:
            release_feature_usage(reservation.cycle_limit_id, db)
            return jsonify({"error": str(exc)}), 400
        orc = _get_orchestrator(
            include_video_analysis=includes_video_analysis(g.current_user),
            agent_weights=weights,
        )
        result = orc.predict_match(home, away, stage=stage, group=group)

        # In knockout stages draws don't exist — resolve to AET/penalties
        knockout_stages = {
            MatchStage.ROUND_OF_32, MatchStage.ROUND_OF_16,
            MatchStage.QUARTER_FINAL, MatchStage.SEMI_FINAL,
            MatchStage.THIRD_PLACE, MatchStage.FINAL,
        }
        if stage in knockout_stages and result.outcome == MatchOutcome.DRAW:
            hw = result.home_win_prob
            aw = result.away_win_prob
            goes_home = _random.random() < hw / (hw + aw)
            result.went_to_penalties = True
            result.most_likely_score = result.most_likely_score + " (AET/PKs)"
            result.outcome = MatchOutcome.HOME_WIN if goes_home else MatchOutcome.AWAY_WIN

        return jsonify(result.to_dict()), 200
    except Exception as exc:
        release_feature_usage(reservation.cycle_limit_id, db)
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
    reservation = reserve_feature_usage(g.current_user, FEATURE_TOURNAMENT_SIMULATION, db)
    if not reservation.allowed:
        return reservation.response

    try:
        weights = _effective_weight_overrides(g.current_user, data)
    except ValueError as exc:
        release_feature_usage(reservation.cycle_limit_id, db)
        return jsonify({"error": str(exc)}), 400
    orc = (
        _get_orchestrator(
            include_video_analysis=includes_video_analysis(g.current_user),
            agent_weights=weights,
        )
        if use_swarm else None
    )
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
        release_feature_usage(reservation.cycle_limit_id, db)
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


@bp.route("/graph/data", methods=["GET"])
@require_user(db)
def graph_data():
    """
    GET /api/predictions/graph/data[?team=France]
    Nodes + edges for the knowledge-graph explorer. Uses the live Zep graph
    when configured, otherwise a static-data synthesis. Cached in-process.
    """
    from ..services.zep_football_tools import ZepFootballTools

    settings = RuntimeSettingsService.current(db)
    tools = ZepFootballTools(api_key=settings.zep_api_key, graph_id=settings.zep_graph_id)
    team = (request.args.get("team") or "").strip() or None
    try:
        return jsonify(tools.get_graph_data(team=team)), 200
    except Exception as exc:
        logger.error(f"Graph data failed: {exc}")
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
# Swarm configuration — per-user agent weights
# ------------------------------------------------------------------

def _swarm_config_payload(user) -> Dict[str, Any]:
    from ..services.agents.weights import AGENT_REGISTRY, WEIGHT_MAX, WEIGHT_MIN

    overrides = _saved_weight_overrides(user)
    return {
        "agents": [
            {
                "key": key,
                "name": spec["name"],
                "description": spec["description"],
                "default": spec["default"],
                "current": overrides.get(key, spec["default"]),
                "min": WEIGHT_MIN,
                "max": WEIGHT_MAX,
            }
            for key, spec in AGENT_REGISTRY.items()
        ],
        "customized": bool(overrides),
    }


@bp.route("/swarm-config", methods=["GET"])
@require_user(db)
def get_swarm_config():
    """GET /api/predictions/swarm-config — agent weights for the current user."""
    return jsonify(_swarm_config_payload(g.current_user)), 200


@bp.route("/swarm-config", methods=["PUT"])
@require_user(db)
def update_swarm_config():
    """
    PUT /api/predictions/swarm-config
    Body: { "weights": {"statistical": 2.0, ...} }  — full desired state,
    keyed by agent key. Values equal to the default are not persisted.
    """
    from ..db.models import UserSwarmPreference
    from ..services.agents.weights import AGENT_REGISTRY, validate_overrides

    data = request.get_json(force=True) or {}
    try:
        cleaned = validate_overrides(data.get("weights") or {})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # Store sparsely: drop entries that match the default
    sparse = {
        key: value
        for key, value in cleaned.items()
        if value != AGENT_REGISTRY[key]["default"]
    }

    pref = db.session.get(UserSwarmPreference, g.current_user.id)
    if sparse:
        if pref is None:
            pref = UserSwarmPreference(user_id=g.current_user.id, weights=sparse)
            db.session.add(pref)
        else:
            pref.weights = sparse
    elif pref is not None:
        db.session.delete(pref)
    db.session.commit()

    return jsonify(_swarm_config_payload(g.current_user)), 200


@bp.route("/swarm-config", methods=["DELETE"])
@require_user(db)
def reset_swarm_config():
    """DELETE /api/predictions/swarm-config — reset to default weights."""
    from ..db.models import UserSwarmPreference

    pref = db.session.get(UserSwarmPreference, g.current_user.id)
    if pref is not None:
        db.session.delete(pref)
        db.session.commit()
    return jsonify(_swarm_config_payload(g.current_user)), 200


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

@bp.route("/live-results", methods=["GET"])
@require_user(db)
def get_live_results():
    """GET /api/predictions/live-results — real WC2026 group-stage results from ESPN."""
    from ..services.data_collectors.live_results import WC2026_RESULTS, refresh_results
    from ..services.tournament_simulator import WC2026_GROUPS

    refresh_results()

    standings: dict = {}
    for g, teams in WC2026_GROUPS.items():
        standings[g] = {
            t: {"team": t, "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "points": 0}
            for t in teams
        }

    for match in WC2026_RESULTS:
        g = match.get("group", "?")
        if g not in standings:
            continue
        home, away = match["home"], match["away"]
        hg, ag = match["home_goals"], match["away_goals"]
        if home not in standings[g] or away not in standings[g]:
            continue
        standings[g][home]["played"] += 1
        standings[g][away]["played"] += 1
        standings[g][home]["gf"] += hg
        standings[g][home]["ga"] += ag
        standings[g][away]["gf"] += ag
        standings[g][away]["ga"] += hg
        if hg > ag:
            standings[g][home]["won"] += 1
            standings[g][home]["points"] += 3
            standings[g][away]["lost"] += 1
        elif hg == ag:
            standings[g][home]["drawn"] += 1
            standings[g][home]["points"] += 1
            standings[g][away]["drawn"] += 1
            standings[g][away]["points"] += 1
        else:
            standings[g][away]["won"] += 1
            standings[g][away]["points"] += 3
            standings[g][home]["lost"] += 1

    sorted_standings: dict = {}
    for g, teams_dict in standings.items():
        ranked = sorted(
            teams_dict.values(),
            key=lambda s: (s["points"], s["gf"] - s["ga"], s["gf"]),
            reverse=True,
        )
        for s in ranked:
            s["gd"] = s["gf"] - s["ga"]
        sorted_standings[g] = ranked

    return jsonify({
        "matches": WC2026_RESULTS,
        "standings": sorted_standings,
        "total": len(WC2026_RESULTS),
    }), 200


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

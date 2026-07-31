"""
Agent weight registry
=====================
Single source of truth for swarm agent ensemble weights.

Stable keys (the API contract for user overrides) map to the display names
used in AgentPrediction.agent_name. User overrides are stored sparsely —
only deviations from the defaults — so default changes propagate to users
who never touched that agent.
"""

from __future__ import annotations

from typing import Dict, Optional

WEIGHT_MIN = 0.0   # 0.0 mutes an agent: it still runs but contributes nothing
WEIGHT_MAX = 3.0

AGENT_REGISTRY: Dict[str, Dict] = {
    "statistical": {
        "name": "Statistical Analysis Agent",
        "default": 1.8,
        "description": "ELO ratings, Poisson model, SofaScore attack/defence stats, H2H records",
    },
    "video": {
        "name": "Video Intelligence Agent",
        "default": 1.0,
        "description": "YouTube highlights engagement ratios, title sentiment, tactical momentum",
    },
    "form": {
        "name": "Recent Form Agent",
        "default": 1.3,
        "description": "Points earned in last 10 official matches, form-adjusted goal rates",
    },
    "tactical": {
        "name": "Tactical Analysis Agent",
        "default": 1.2,
        "description": "Style-matchup matrix (high-press vs counter, tiki-taka vs block)",
    },
    "live_data": {
        "name": "Live Data Agent",
        "default": 1.4,
        "description": "FotMob xG and heatmaps, FlashScore live form",
    },
    "market_signals": {
        "name": "Market Signals Agent",
        "default": 0.8,
        "description": "365Scores odds movement and prediction-market signals",
    },
    "squad_quality": {
        "name": "Squad Quality Agent",
        "default": 1.1,
        "description": "Opta player ratings, squad depth and availability",
    },
}

_NAME_BY_KEY = {key: spec["name"] for key, spec in AGENT_REGISTRY.items()}


def clamp_weight(value: float) -> float:
    return max(WEIGHT_MIN, min(WEIGHT_MAX, float(value)))


def validate_overrides(overrides: Dict) -> Dict[str, float]:
    """
    Validate a sparse override dict from the API.
    Returns {agent_key: clamped_float}. Raises ValueError on unknown keys
    or non-numeric values.
    """
    if not isinstance(overrides, dict):
        raise ValueError("weights must be an object of {agent_key: number}")

    cleaned: Dict[str, float] = {}
    for key, value in overrides.items():
        if key not in AGENT_REGISTRY:
            raise ValueError(f"unknown agent key: {key}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"weight for {key} must be a number")
        cleaned[key] = clamp_weight(value)
    return cleaned


def resolve_weights(overrides: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """
    Return display-name-keyed weights: defaults merged with clamped overrides
    (overrides are keyed by stable agent key).
    """
    resolved = {spec["name"]: spec["default"] for spec in AGENT_REGISTRY.values()}
    for key, value in (overrides or {}).items():
        name = _NAME_BY_KEY.get(key)
        if name is not None:
            resolved[name] = clamp_weight(value)
    return resolved


def weights_by_key(overrides: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """Return agent-key-keyed effective weights (for API responses)."""
    return {
        key: clamp_weight((overrides or {}).get(key, spec["default"]))
        for key, spec in AGENT_REGISTRY.items()
    }

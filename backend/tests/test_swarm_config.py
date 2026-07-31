from __future__ import annotations

from app.db.base import db
from app.db.models import UserSwarmPreference
from app.models.match import AgentPrediction, MatchStage
from app.services.agents.aggregator_agent import AggregatorAgent
from app.services.agents.weights import (
    AGENT_REGISTRY,
    WEIGHT_MAX,
    WEIGHT_MIN,
    resolve_weights,
    validate_overrides,
    weights_by_key,
)


def _auth_header(clerk_user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {clerk_user_id}"}


def _auth(monkeypatch):
    def claims(token):
        email = "admin@example.com" if token == "user_admin" else "user@example.com"
        return {"sub": token, "email": email}

    monkeypatch.setattr("app.auth.verify_session_token", claims)


# ---------------------------------------------------------------------------
# weights module
# ---------------------------------------------------------------------------

def test_resolve_weights_defaults():
    resolved = resolve_weights(None)
    assert resolved["Statistical Analysis Agent"] == 1.8
    assert resolved["Market Signals Agent"] == 0.8
    assert len(resolved) == len(AGENT_REGISTRY)


def test_resolve_weights_applies_and_clamps_overrides():
    resolved = resolve_weights({"statistical": 9.9, "video": -1.0, "form": 2.0})
    assert resolved["Statistical Analysis Agent"] == WEIGHT_MAX
    assert resolved["Video Intelligence Agent"] == WEIGHT_MIN
    assert resolved["Recent Form Agent"] == 2.0
    assert resolved["Tactical Analysis Agent"] == 1.2  # untouched default


def test_validate_overrides_rejects_unknown_keys_and_bad_values():
    import pytest

    with pytest.raises(ValueError):
        validate_overrides({"not_an_agent": 1.0})
    with pytest.raises(ValueError):
        validate_overrides({"statistical": "high"})
    with pytest.raises(ValueError):
        validate_overrides({"statistical": True})
    with pytest.raises(ValueError):
        validate_overrides("not a dict")


def test_weights_by_key_merges_overrides():
    merged = weights_by_key({"video": 0.0})
    assert merged["video"] == 0.0
    assert merged["statistical"] == 1.8
    assert set(merged) == set(AGENT_REGISTRY)


# ---------------------------------------------------------------------------
# aggregator behaviour
# ---------------------------------------------------------------------------

def _pred(agent_name: str, hw: float, aw: float, confidence: float = 0.8) -> AgentPrediction:
    dr = max(0.0, 1.0 - hw - aw)
    return AgentPrediction(
        agent_name=agent_name,
        home_win_prob=hw,
        draw_prob=dr,
        away_win_prob=aw,
        predicted_home_goals=1.5,
        predicted_away_goals=1.0,
        confidence=confidence,
        reasoning="test",
    )


def test_aggregator_respects_custom_weights():
    preds = [
        _pred("Statistical Analysis Agent", hw=0.9, aw=0.05),
        _pred("Recent Form Agent", hw=0.05, aw=0.9),
    ]
    agg = AggregatorAgent(llm_client=None)

    stat_heavy = agg.aggregate("A", "B", MatchStage.FINAL, None, preds, weights={"statistical": 3.0, "form": 0.1})
    form_heavy = agg.aggregate("A", "B", MatchStage.FINAL, None, preds, weights={"statistical": 0.1, "form": 3.0})

    assert stat_heavy.home_win_prob > 0.6
    assert form_heavy.away_win_prob > 0.6
    assert stat_heavy.weights_used["statistical"] == 3.0
    assert form_heavy.weights_used["form"] == 3.0


def test_aggregator_muted_agent_contributes_nothing():
    preds = [
        _pred("Statistical Analysis Agent", hw=0.9, aw=0.05),
        _pred("Recent Form Agent", hw=0.1, aw=0.8),
    ]
    agg = AggregatorAgent(llm_client=None)
    result = agg.aggregate("A", "B", MatchStage.FINAL, None, preds, weights={"form": 0.0})
    # Only the statistical agent should shape the ensemble
    assert abs(result.home_win_prob - 0.9) < 0.02


def test_aggregator_all_muted_falls_back_without_crash():
    preds = [_pred("Statistical Analysis Agent", hw=0.7, aw=0.1)]
    agg = AggregatorAgent(llm_client=None)
    result = agg.aggregate(
        "A", "B", MatchStage.FINAL, None, preds,
        weights={key: 0.0 for key in AGENT_REGISTRY},
    )
    assert 0.0 <= result.home_win_prob <= 1.0


# ---------------------------------------------------------------------------
# swarm-config API
# ---------------------------------------------------------------------------

def test_get_swarm_config_defaults(client, user, monkeypatch):
    _auth(monkeypatch)
    resp = client.get("/api/predictions/swarm-config", headers=_auth_header(user["clerk_user_id"]))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["customized"] is False
    by_key = {a["key"]: a for a in body["agents"]}
    assert by_key["statistical"]["current"] == 1.8
    assert by_key["statistical"]["default"] == 1.8
    assert set(by_key) == set(AGENT_REGISTRY)


def test_put_swarm_config_persists_sparsely(client, app, user, monkeypatch):
    _auth(monkeypatch)
    resp = client.put(
        "/api/predictions/swarm-config",
        json={"weights": {"statistical": 2.5, "video": 1.0}},  # video == default
        headers=_auth_header(user["clerk_user_id"]),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["customized"] is True
    by_key = {a["key"]: a for a in body["agents"]}
    assert by_key["statistical"]["current"] == 2.5
    assert by_key["video"]["current"] == 1.0

    with app.app_context():
        pref = db.session.get(UserSwarmPreference, user["id"])
        assert pref.weights == {"statistical": 2.5}  # default-valued entry dropped


def test_put_swarm_config_rejects_unknown_agent(client, user, monkeypatch):
    _auth(monkeypatch)
    resp = client.put(
        "/api/predictions/swarm-config",
        json={"weights": {"bogus": 2.0}},
        headers=_auth_header(user["clerk_user_id"]),
    )
    assert resp.status_code == 400


def test_put_all_defaults_deletes_row(client, app, user, monkeypatch):
    _auth(monkeypatch)
    client.put(
        "/api/predictions/swarm-config",
        json={"weights": {"statistical": 2.5}},
        headers=_auth_header(user["clerk_user_id"]),
    )
    resp = client.put(
        "/api/predictions/swarm-config",
        json={"weights": {"statistical": 1.8}},
        headers=_auth_header(user["clerk_user_id"]),
    )
    assert resp.get_json()["customized"] is False
    with app.app_context():
        assert db.session.get(UserSwarmPreference, user["id"]) is None


def test_delete_swarm_config_resets(client, app, user, monkeypatch):
    _auth(monkeypatch)
    client.put(
        "/api/predictions/swarm-config",
        json={"weights": {"form": 0.2}},
        headers=_auth_header(user["clerk_user_id"]),
    )
    resp = client.delete("/api/predictions/swarm-config", headers=_auth_header(user["clerk_user_id"]))
    assert resp.status_code == 200
    assert resp.get_json()["customized"] is False
    with app.app_context():
        assert db.session.get(UserSwarmPreference, user["id"]) is None


def test_swarm_config_requires_auth(client):
    assert client.get("/api/predictions/swarm-config").status_code in (401, 403)

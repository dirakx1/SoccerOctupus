from __future__ import annotations

from app.services.zep_football_tools import ZepFootballTools, _GRAPH_CACHE


def _auth_header(clerk_user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {clerk_user_id}"}


def _auth(monkeypatch):
    monkeypatch.setattr(
        "app.auth.verify_session_token",
        lambda token: {"sub": token, "email": "user@example.com"},
    )


def _tools() -> ZepFootballTools:
    _GRAPH_CACHE.clear()
    return ZepFootballTools(api_key=None, graph_id=None)


def test_static_graph_data_shape():
    data = _tools().get_graph_data()
    assert data["mode"] == "static_fallback"
    assert data["counts"]["nodes"] == len(data["nodes"])
    assert data["counts"]["edges"] == len(data["edges"])

    types = {n["type"] for n in data["nodes"]}
    assert {"team", "group"} <= types

    node_ids = {n["id"] for n in data["nodes"]}
    for e in data["edges"]:
        assert e["source"] in node_ids
        assert e["target"] in node_ids

    edge_names = {e["name"] for e in data["edges"]}
    assert "PLAYS_IN_GROUP" in edge_names


def test_static_graph_has_48_teams_and_12_groups():
    data = _tools().get_graph_data()
    teams = [n for n in data["nodes"] if n["type"] == "team"]
    groups = [n for n in data["nodes"] if n["type"] == "group"]
    assert len(teams) == 48
    assert len(groups) == 12


def test_ego_graph_filter():
    tools = _tools()
    data = tools.get_graph_data(team="France")
    labels = {n["label"] for n in data["nodes"]}
    assert "France" in labels
    assert 0 < len(data["nodes"]) < 60
    # Every edge must touch a France-matched seed node
    seed_ids = {n["id"] for n in data["nodes"] if "france" in n["label"].lower()}
    assert all(
        e["source"] in seed_ids or e["target"] in seed_ids
        for e in data["edges"]
    )


def test_ego_graph_unknown_team_returns_empty():
    data = _tools().get_graph_data(team="Atlantis")
    assert data["nodes"] == []
    assert data["edges"] == []


def test_graph_data_is_cached():
    tools = _tools()
    first = tools.get_graph_data()
    second = tools.get_graph_data()
    assert first is second  # same object → served from cache


def test_graph_data_endpoint(client, user, monkeypatch):
    _auth(monkeypatch)
    resp = client.get(
        "/api/predictions/graph/data",
        headers=_auth_header(user["clerk_user_id"]),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["mode"] in ("zep_graph", "static_fallback")
    assert body["counts"]["nodes"] > 0


def test_graph_data_endpoint_requires_auth(client):
    assert client.get("/api/predictions/graph/data").status_code in (401, 403)

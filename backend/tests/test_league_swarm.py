from app.leagues.swarm import build_league_swarm


def test_uncalibrated_numeric_provider_abstains_from_consensus():
    result = build_league_swarm(
        {"probabilities": {"home": 0.5, "draw": 0.25, "away": 0.25}},
        [{"provider": "365Scores", "status": "admitted", "source": "odds", "evidence": {"homeImplied": .6, "drawImplied": .2, "awayImplied": .2}}],
    )
    assert abs(sum(result["probabilities"].values()) - 1) < 1e-9
    assert result["contributions"] == [{"name": "Statistical", "source": "ESPN completed results", "weight": 1.0}]
    assert result["abstentions"][0]["name"] == "365Scores"


def test_persisted_calibrated_provider_contributes_to_consensus():
    result = build_league_swarm(
        {"probabilities": {"home": 0.4, "draw": 0.3, "away": 0.3}},
        [{"provider": "365Scores", "status": "admitted", "source": "odds", "evidence": {"homeImplied": .7, "drawImplied": .2, "awayImplied": .1}}],
        calibrated_weights={"365Scores": 0.5},
    )
    assert result["probabilities"]["home"] == 0.5
    assert result["contributions"][-1]["weight"] == 0.5


def test_sofascore_uses_the_fixture_club_keys_and_attack_defence_rates():
    result = build_league_swarm(
        {"homeTeam": {"name": "Arsenal"}, "awayTeam": {"name": "Chelsea"}, "probabilities": {"home": .4, "draw": .3, "away": .3}},
        [{"provider": "SofaScore", "status": "admitted", "source": "clubs", "evidence": {
            "Arsenal": {"goalsForPerMatch": 2.0, "goalsAgainstPerMatch": 1.0},
            "Chelsea": {"goalsForPerMatch": 1.0, "goalsAgainstPerMatch": 1.5},
        }}],
    )
    assert result["contributions"] == [{"name": "Statistical", "source": "ESPN completed results", "weight": 1.0}]
    assert result["abstentions"][0]["name"] == "SofaScore"


def test_unavailable_and_identity_only_agents_abstain():
    result = build_league_swarm(
        {"probabilities": {"home": 0.5, "draw": 0.25, "away": 0.25}},
        [{"provider": "YouTube", "status": "admitted", "source": "videos", "evidence": {"teams": {}}}, {"provider": "Opta", "status": "unavailable", "reason": "not configured"}],
    )
    assert {row["name"] for row in result["abstentions"]} == {"YouTube", "Opta"}
    assert not any(row["name"] in {"YouTube", "Opta"} for row in result["contributions"])
    assert next(row for row in result["specialists"] if row["name"] == "YouTube")["status"] == "evidence-only"


def test_malformed_numeric_provider_cannot_enter_consensus():
    result = build_league_swarm(
        {"probabilities": {"home": .4, "draw": .3, "away": .3}},
        [{"provider": "365Scores", "status": "admitted", "evidence": {"homeImplied": "bad", "drawImplied": .2, "awayImplied": .8}}],
    )
    assert result["abstentions"][0]["name"] == "365Scores"

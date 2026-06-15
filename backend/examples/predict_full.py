#!/usr/bin/env python3
"""
predict_full.py — Full 6-agent swarm prediction with all data sources.
=======================================================================
Runs every step of the prediction pipeline in the correct order and
prints a rich, structured report.

Usage:
    # Random group-stage fixture
    python3 backend/examples/predict_full.py

    # Specific match
    python3 backend/examples/predict_full.py --home Argentina --away France --stage final

    # Skip the runtime settings check (if you've already verified it)
    python3 backend/examples/predict_full.py --home Brazil --away Spain --no-check

    # Save JSON output to file
    python3 backend/examples/predict_full.py --home Germany --away Portugal --out /tmp/pred.json
"""

import argparse
import json
import os
import sys
import time

# ── Load .env ─────────────────────────────────────────────────────────────────
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_env = os.path.join(_root, ".env")
if os.path.exists(_env):
    with open(_env) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

sys.path.insert(0, os.path.join(_root, "backend"))

from app.models.match import MatchOutcome, MatchStage
from app import create_app
from app.db.base import db
from app.runtime_settings import RuntimeSettings, RuntimeSettingsService
from app.services.swarm_orchestrator import SwarmOrchestrator
from app.services.zep_football_tools import ZepFootballTools
from app.services.tournament_simulator import WC2026_GROUPS
from app.services.data_collectors.sofascore_collector import TEAM_STATIC_DATA

SEP  = "═" * 66
SEP2 = "─" * 66

# ── Agent descriptions ────────────────────────────────────────────────────────
AGENT_META = {
    "Statistical Analysis Agent": ("📊", "SofaScore ELO + Poisson model + H2H",        1.8),
    "Video Intelligence Agent":   ("🎥", "YouTube highlights + sentiment",              1.0),
    "Recent Form Agent":          ("🔥", "Last-10-match form points",                   1.3),
    "Tactical Analysis Agent":    ("🧠", "Style matchup matrix + Zep graph",             1.2),
    "Live Data Agent":            ("📡", "FotMob xG + heatmaps + FlashScore H2H",       1.4),
    "Market Signals Agent":       ("💹", "365Scores odds + Tiki-Taka AI (Dixon-Coles)", 0.8),
    "Squad Quality Agent":        ("⚽", "Opta player ratings + squad depth + set pieces", 1.1),
}


# ─────────────────────────────────────────────────────────────────────────────
# Step 0 — Environment check
# ─────────────────────────────────────────────────────────────────────────────

def load_runtime_settings() -> RuntimeSettings:
    app = create_app()
    with app.app_context():
        return RuntimeSettingsService.current(db)


def check_environment(settings: RuntimeSettings) -> dict:
    checks = {}

    # Zep
    checks["zep_key"]   = bool(settings.zep_api_key)
    checks["zep_graph"] = bool(settings.zep_graph_id)

    # LLM
    checks["llm_key"]   = bool(settings.llm_api_key)
    checks["llm_url_ok"] = settings.llm_base_url.endswith("/v1")
    checks["llm_model"] = bool(settings.llm_model_name)

    # YouTube (optional)
    checks["youtube"] = bool(settings.youtube_api_key)

    return checks


def print_env_check(checks: dict, settings: RuntimeSettings):
    print(SEP)
    print("  STEP 0 — Runtime settings check")
    print(SEP)

    def row(label, ok, note=""):
        icon = "✓" if ok else "✗"
        suffix = f"  ({note})" if note else ""
        print(f"  {icon}  {label}{suffix}")

    row("Zep API key",   checks["zep_key"],   "" if checks["zep_key"] else "set in /admin/settings")
    row("Zep graph ID",  checks["zep_graph"], "" if checks["zep_graph"] else "run: python3 backend/setup_zep.py")
    row("LLM API key",   checks["llm_key"],   "" if checks["llm_key"] else "optional — narrative synthesis disabled")
    row("LLM base URL ends /v1", checks["llm_url_ok"],
        "" if checks["llm_url_ok"] else f"current: {settings.llm_base_url} — add /v1")
    row("YouTube API key", checks["youtube"], "optional — synthetic scores used if absent")

    zep_mode = "Zep knowledge graph (live)" if (checks["zep_key"] and checks["zep_graph"]) else "static data fallback"
    llm_mode = f"{settings.llm_model_name} via {settings.llm_base_url}" if checks["llm_key"] else "disabled"
    yt_mode  = "YouTube Data API v3 (live)" if checks["youtube"] else "synthetic ELO-based scores"

    print()
    print(f"  Knowledge layer : {zep_mode}")
    print(f"  Narrative LLM   : {llm_mode}")
    print(f"  Video signals   : {yt_mode}")
    print()

    critical_ok = checks["zep_key"] or True  # system works without Zep via fallback
    if not checks["llm_url_ok"] and checks["llm_key"]:
        print("  ⚠️  LLM_BASE_URL must end with /v1 for OpenAI-compatible calls.")
        print("     Fix in /admin/settings, for example: https://api.anthropic.com/v1")
        print()
    return critical_ok


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Select fixture
# ─────────────────────────────────────────────────────────────────────────────

def select_fixture(home_arg, away_arg):
    if home_arg and away_arg:
        group = next(
            (g for g, teams in WC2026_GROUPS.items()
             if home_arg in teams and away_arg in teams),
            None
        )
        return home_arg, away_arg, group

    import random, itertools
    fixtures = [(g, h, a) for g, teams in WC2026_GROUPS.items()
                for h, a in itertools.combinations(teams, 2)]
    group, home, away = random.choice(fixtures)
    print(f"  🎲  Randomly selected: Group {group} — {home} vs {away}")
    return home, away, group


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Build swarm
# ─────────────────────────────────────────────────────────────────────────────

def build_swarm(checks: dict, settings: RuntimeSettings):
    print(SEP)
    print("  STEP 2 — Initialising 6-agent swarm")
    print(SEP)

    llm_client = None
    if checks.get("llm_key") and checks.get("llm_url_ok"):
        try:
            from app.utils.llm_client import LLMClient
            llm_client = LLMClient(settings=settings)
            print(f"  ✓  LLM client: {settings.llm_model_name}")
        except Exception as e:
            print(f"  ⚠  LLM init failed ({e}) — narrative disabled")

    zep_tools = ZepFootballTools(api_key=settings.zep_api_key, graph_id=settings.zep_graph_id)
    mode = "Zep graph" if zep_tools.has_graph else "static data"
    print(f"  ✓  Knowledge layer: {mode}")

    orc = SwarmOrchestrator(settings=settings, llm_client=llm_client, zep_tools=zep_tools)

    print()
    print("  Agents:")
    for agent in orc.agents:
        icon, desc, weight = AGENT_META.get(agent.name, ("🤖", "", agent.weight))
        print(f"    {icon}  {agent.name:<32}  weight={weight}  {desc}")
    print()
    return orc


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Run swarm prediction
# ─────────────────────────────────────────────────────────────────────────────

def run_swarm(orc, home, away, stage_str, group):
    stage = MatchStage(stage_str)

    print(SEP)
    print(f"  STEP 3 — Running swarm: {home} vs {away}")
    print(SEP)

    agent_timings = {}
    start_total = time.time()
    completed_agents = []

    def progress(s, pct, msg):
        if s == "running" and pct > 0:
            # Extract agent name from message
            for name in AGENT_META:
                short = name.split()[0]
                if short in msg:
                    agent_timings[name] = time.time() - start_total
            bar = "▓" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"  [{bar}] {pct:3d}%  {msg}")
        elif pct == 100:
            bar = "▓" * 20
            print(f"  [{bar}] {pct:3d}%  {msg}")

    pred = orc.predict_match(
        home_team=home,
        away_team=away,
        stage=stage,
        group=group,
        progress_callback=progress,
    )
    pred._elapsed = round(time.time() - start_total, 2)
    pred._agent_timings = agent_timings
    print(f"\n  Swarm completed in {pred._elapsed}s")
    return pred


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Print full report
# ─────────────────────────────────────────────────────────────────────────────

def _prob_bar(p: float, w: int = 22) -> str:
    filled = round(p * w)
    return "█" * filled + "░" * (w - filled)

def _stars(c: float) -> str:
    s = round(c * 5)
    return "★" * s + "☆" * (5 - s)

def _elo(t): return TEAM_STATIC_DATA.get(t, {}).get("elo", "?")
def _rank(t): return TEAM_STATIC_DATA.get(t, {}).get("rank", "?")
def _style(t): return TEAM_STATIC_DATA.get(t, {}).get("style", "balanced")


def print_report(pred, home, away, stage_str, group):
    is_group = pred.stage == MatchStage.GROUP
    stage_note = "Draws allowed — 1 pt each" if is_group else "Knockout — winner by 90 min, AET or PKs"
    stage_label = stage_str.replace("_", " ").title()

    print()
    print(SEP)
    print(f"  🐙  FifaOctopus — Full Swarm Match Prediction")
    print(f"  FIFA World Cup 2026  ·  {stage_label}")
    if group:
        print(f"  Group {group}  ·  {stage_note}")
    else:
        print(f"  {stage_note}")
    print(SEP)
    print()

    # ── Teams ────────────────────────────────────────────────────────────
    print(f"  {'HOME':>30}         {'AWAY'}")
    print(f"  {home:>30}   vs   {away}")
    print(f"  {'ELO ' + str(_elo(home)):>30}         ELO {_elo(away)}")
    print(f"  {'FIFA #' + str(_rank(home)):>30}         FIFA #{_rank(away)}")
    print(f"  {_style(home):>30}         {_style(away)}")
    print()
    print(SEP2)

    # ── Probabilities ────────────────────────────────────────────────────
    hw, dr, aw = pred.home_win_prob, pred.draw_prob, pred.away_win_prob
    print()
    print("  SWARM PROBABILITIES")
    print()
    print(f"  {home} win  {_prob_bar(hw)}  {hw:>5.1%}")
    print(f"  Draw        {_prob_bar(dr)}  {dr:>5.1%}")
    print(f"  {away} win  {_prob_bar(aw)}  {aw:>5.1%}")
    print()

    # ── Result ───────────────────────────────────────────────────────────
    outcome_str = (
        f"{home} WIN"      if pred.outcome == MatchOutcome.HOME_WIN
        else f"{away} WIN" if pred.outcome == MatchOutcome.AWAY_WIN
        else "DRAW"
    )
    if pred.went_to_penalties:
        outcome_str += "  →  resolved AET / Penalties"
    elif is_group and pred.outcome == MatchOutcome.DRAW:
        outcome_str += "  (both earn 1 pt)"

    print(f"  Predicted score   :  {pred.most_likely_score}")
    print(f"  Predicted outcome :  {outcome_str}")
    if is_group:
        pts = {"home_win": (3, 0), "draw": (1, 1), "away_win": (0, 3)}
        hp, ap = pts[pred.outcome.value]
        print(f"  Points awarded    :  {home} +{hp}pt  /  {away} +{ap}pt")
    print(f"  Swarm confidence  :  {_stars(pred.overall_confidence)}  ({pred.overall_confidence:.0%})")
    print(f"  Swarm time        :  {getattr(pred, '_elapsed', '?')}s")
    print()
    print(SEP2)

    # ── Agent breakdown ──────────────────────────────────────────────────
    print()
    print("  AGENT BREAKDOWN  (7 agents · parallel execution)")
    print()
    for ap in pred.agent_predictions:
        icon, desc, weight = AGENT_META.get(ap.agent_name, ("🤖", "", 1.0))
        winner = (
            "← HOME" if ap.home_win_prob > ap.away_win_prob + 0.05
            else ("AWAY →" if ap.away_win_prob > ap.home_win_prob + 0.05
                  else "≈ EVEN")
        )
        print(f"  {icon}  {ap.agent_name}  (weight {weight}×)")
        print(f"     H {ap.home_win_prob:.1%}  D {ap.draw_prob:.1%}  A {ap.away_win_prob:.1%}"
              f"  │  xG {ap.predicted_home_goals:.1f}–{ap.predicted_away_goals:.1f}"
              f"  │  conf {ap.confidence:.0%}  {winner}")
        # Wrap reasoning
        words, line, lines = ap.reasoning.split(), "", []
        for w in words:
            if len(line) + len(w) + 1 > 60:
                lines.append(line)
                line = w
            else:
                line = (line + " " + w).strip()
        if line:
            lines.append(line)
        for i, ln in enumerate(lines[:3]):   # cap at 3 lines
            print(f"     {'  ' if i else '→ '}{ln}")
        srcs = ", ".join(ap.data_sources[:2])
        print(f"     Sources: {srcs}")
        print()

    print(SEP2)

    # ── Key factors ──────────────────────────────────────────────────────
    if pred.key_factors:
        print()
        print("  KEY FACTORS")
        print()
        for f in pred.key_factors:
            print(f"  •  {f}")
        print()

    # ── LLM narrative ────────────────────────────────────────────────────
    if pred.swarm_consensus:
        print(SEP2)
        print()
        print("  SWARM CONSENSUS  (LLM synthesis)")
        print()
        words, line = pred.swarm_consensus.split(), ""
        for w in words:
            if len(line) + len(w) + 1 > 62:
                print(f"  {line}")
                line = w
            else:
                line = (line + " " + w).strip()
        if line:
            print(f"  {line}")
        print()

    print(SEP)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Prediction market questions
# ─────────────────────────────────────────────────────────────────────────────

def print_market_questions(pred):
    from app.services.market_question_generator import MarketQuestionGenerator
    gen = MarketQuestionGenerator()
    questions = gen.from_match(pred)

    print(SEP)
    print("  STEP 5 — Prediction Market Questions")
    print("  Ready to list on Kalshi (kalshi.com) or Polymarket (polymarket.com)")
    print(SEP)
    print()

    PROP_ICONS = {
        "match_winner": "🏆",
        "draw":         "🤝",
        "btts":         "⚽",
        "over_under":   "📈",
        "clean_sheet":  "🛡️ ",
        "penalties":    "🥅",
        "correct_score":"🎯",
    }

    for q in questions:
        icon = PROP_ICONS.get(q.prop_type, "📊")
        yes_bar = "█" * int(q.yes_probability * 20) + "░" * (20 - int(q.yes_probability * 20))
        no_bar  = "█" * int(q.no_probability * 20)  + "░" * (20 - int(q.no_probability * 20))
        print(f"  {icon}  {q.short_title}")
        print(f"     {q.question}")
        print(f"     YES {yes_bar} {q.yes_probability:.1%}   ·   Kalshi {q.kalshi_yes_cents:.1f}¢  /  Polymarket ${q.polymarket_yes_usdc:.4f}")
        print(f"     NO  {no_bar} {q.no_probability:.1%}   ·   Kalshi {100-q.kalshi_yes_cents:.1f}¢  /  Polymarket ${1-q.polymarket_yes_usdc:.4f}")
        print(f"     Resolves: {q.resolution_date}  ·  ID: {q.question_id}")
        print()

    print(SEP2)
    print(f"  {len(questions)} questions generated from FifaOctopus swarm probabilities.")
    print("  Prices reflect fair-value estimates — no bookmaker margin applied.")
    print("  Resolution source: FIFA official results (fifa.com)")
    print()
    print(SEP)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Save JSON (optional)
# ─────────────────────────────────────────────────────────────────────────────

def save_json(pred, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(pred.to_dict(), f, indent=2)
    print(f"  JSON saved to: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FifaOctopus 6-agent full prediction")
    parser.add_argument("--home", default=None)
    parser.add_argument("--away", default=None)
    parser.add_argument("--stage", default="group",
                        choices=["group","round_of_32","round_of_16",
                                 "quarter_final","semi_final","final"])
    parser.add_argument("--no-check", action="store_true",
                        help="Skip runtime settings check")
    parser.add_argument("--out", default=None, metavar="FILE",
                        help="Save prediction JSON to this path")
    args = parser.parse_args()

    # Step 0
    settings = load_runtime_settings()
    checks = check_environment(settings)
    if not args.no_check:
        print_env_check(checks, settings)

    # Step 1
    print(SEP)
    print("  STEP 1 — Selecting fixture")
    print(SEP)
    home, away, group = select_fixture(args.home, args.away)
    print(f"  Match  : {home} (home)  vs  {away} (away)")
    print(f"  Stage  : {args.stage.replace('_',' ').title()}")
    if group:
        print(f"  Group  : {group}")
    print()

    # Step 2
    orc = build_swarm(checks, settings)

    # Step 3
    pred = run_swarm(orc, home, away, args.stage, group)

    # Step 4
    print_report(pred, home, away, args.stage, group)

    # Step 5
    print_market_questions(pred)

    # Step 6
    if args.out:
        save_json(pred, args.out)


if __name__ == "__main__":
    main()

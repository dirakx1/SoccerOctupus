#!/usr/bin/env python3
"""
setup_zep.py — One-shot Zep knowledge graph builder for FifaOctopus.

Run this ONCE after saving a Zep API key in /admin/settings.
It builds the WC2026 football knowledge graph and saves the graph_id
back to admin settings.

Usage:
    cd /Users/mac/FifaOctopus
    python3 backend/setup_zep.py
"""

import os
import sys
import time

# ── load .env if present ─────────────────────────────────────────────────────
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env = os.path.join(_root, ".env")
if os.path.exists(_env):
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, os.path.join(_root, "backend"))

from app import create_app
from app.db.base import db
from app.runtime_settings import RuntimeSettingsService

app = create_app()

# ── validate key ─────────────────────────────────────────────────────────────
with app.app_context():
    runtime_settings = RuntimeSettingsService.current(db)

api_key = runtime_settings.zep_api_key
if not api_key:
    print("\n  ✗  Zep API key is not configured.")
    print("     Get a free key at https://app.getzep.com/")
    print("     Then save it in /admin/settings and rerun this script.\n")
    sys.exit(1)

print()
print("═" * 60)
print("  🐙  FifaOctopus — Zep Knowledge Graph Builder")
print("═" * 60)
print()
print("  Building the WC2026 football knowledge graph.")
print("  This runs once — future predictions reuse the graph.")
print()

# ── import builder ────────────────────────────────────────────────────────────
from app.services.zep_football_graph import ZepFootballGraphBuilder

builder = ZepFootballGraphBuilder(api_key=api_key)

start = time.time()

def progress(pct: int, msg: str):
    bar = "▓" * (pct // 5) + "░" * (20 - pct // 5)
    print(f"  [{bar}] {pct:3d}%  {msg}")

try:
    graph_id = builder.build(progress_callback=progress)
except Exception as exc:
    print(f"\n  ✗  Graph build failed: {exc}")
    sys.exit(1)

with app.app_context():
    settings = RuntimeSettingsService.ensure_defaults(db)
    settings.zep_graph_id = graph_id
    db.session.commit()

elapsed = time.time() - start
print()
print("─" * 60)
print(f"  ✓  Graph built in {elapsed:.0f}s")
print()
print(f"  graph_id: {graph_id}")
print()
print("  Saved this graph ID to /admin/settings.")
print("  Then start the server:")
print()
print("    npm run dev")
print()
print("  Or predict a match right now:")
print()
print("    python3 backend/examples/predict_random_match.py --seed 17")
print()
print("═" * 60)

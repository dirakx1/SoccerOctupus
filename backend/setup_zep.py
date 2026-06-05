#!/usr/bin/env python3
"""
setup_zep.py — One-shot Zep knowledge graph builder for FifaOctopus.

Run this ONCE after setting ZEP_API_KEY in your .env file.
It builds the WC2026 football knowledge graph and prints the graph_id
to copy into your .env as ZEP_GRAPH_ID.

Usage:
    cd /Users/mac/FifaOctopus
    python3 backend/setup_zep.py

    # Or pass key directly without .env:
    ZEP_API_KEY=zep-... python3 backend/setup_zep.py
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

# ── validate key ─────────────────────────────────────────────────────────────
api_key = os.environ.get("ZEP_API_KEY", "")
if not api_key or api_key == "your_zep_api_key":
    print("\n  ✗  ZEP_API_KEY is not set.")
    print("     Get a free key at https://app.getzep.com/")
    print("     Then add it to /Users/mac/FifaOctopus/.env:\n")
    print("       ZEP_API_KEY=zep-xxxxxxxxxxxxxxxx\n")
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

elapsed = time.time() - start
print()
print("─" * 60)
print(f"  ✓  Graph built in {elapsed:.0f}s")
print()
print(f"  graph_id: {graph_id}")
print()
print("  Next step — add this to your .env file:")
print()
print(f"    ZEP_GRAPH_ID={graph_id}")
print()
print("  Then start the server:")
print()
print("    npm run dev")
print()
print("  Or predict a match right now:")
print()
print(f"    ZEP_GRAPH_ID={graph_id} python3 backend/examples/predict_random_match.py --seed 17")
print()
print("═" * 60)

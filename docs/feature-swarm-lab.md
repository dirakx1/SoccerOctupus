# Feature Draft: Swarm Lab — Custom Agent Weights & Knowledge Graph Explorer

Status: draft · Author: Claude (with Rafael) · Date: 2026-07-30

## Summary

A new workspace area, **Swarm Lab**, with two capabilities:

1. **Agent Weights** — signed-in users tune the influence of each swarm agent
   (Statistical, Video, Form, Tactical, Live Data, Market Signals, Squad Quality)
   on their own predictions, with per-user persistence and per-request overrides.
2. **Knowledge Graph** — an interactive visualization of the Zep football
   knowledge graph the agents query (teams, groups, results, styles), with a
   static-data fallback when Zep is not configured.

Why it fits the product: it turns the swarm from a black box into something
users can steer and inspect — the core differentiator of SoccerOctopus — and it
is a natural premium surface.

---

## Part 1 — Editable agent weights

### Current state

- `BaseAgent.__init__(name, weight)` stores a weight that is **never used**.
- `AggregatorAgent.aggregate()` re-declares a hardcoded `AGENT_WEIGHTS` dict
  keyed by display name (e.g. `"Statistical Analysis Agent": 1.8`) and uses
  `weight × confidence` for the ensemble. This is the only weight that matters.
- Nothing is user-configurable.

### Design

**Single source of truth** — new module `backend/app/services/agents/weights.py`:

```python
# Stable keys (API contract) → display name, default weight, bounds
AGENT_REGISTRY = {
    "statistical":    {"name": "Statistical Analysis Agent", "default": 1.8},
    "video":          {"name": "Video Intelligence Agent",   "default": 1.0},
    "form":           {"name": "Recent Form Agent",          "default": 1.3},
    "tactical":       {"name": "Tactical Analysis Agent",    "default": 1.2},
    "live_data":      {"name": "Live Data Agent",            "default": 1.4},
    "market_signals": {"name": "Market Signals Agent",       "default": 0.8},
    "squad_quality":  {"name": "Squad Quality Agent",        "default": 1.1},
}
WEIGHT_MIN, WEIGHT_MAX = 0.0, 3.0   # 0.0 = mute the agent entirely

def resolve_weights(overrides: dict | None) -> dict[str, float]:
    """Display-name-keyed weights: defaults merged with clamped overrides."""
```

`AggregatorAgent.aggregate(..., weights: dict | None = None)` uses
`resolve_weights()`; the hardcoded dict is deleted. `SwarmOrchestrator`
gains `agent_weights` in `__init__` and passes them to the aggregator.
A weight of `0.0` short-circuits: the agent still runs (its card is shown)
but contributes nothing to the ensemble. Optional optimization: skip
running muted agents to save latency/API calls.

**Persistence** — new table via Alembic migration:

```
user_swarm_preferences
  user_id      FK users.id, PK
  weights      JSON        # {"statistical": 2.0, "video": 0.5, ...} sparse
  updated_at   DateTime
```

Sparse storage: only deviations from defaults are stored, so changing a
default later applies to everyone who didn't touch that slider.

**API** (all `require_user`, in `predictions.py` or a new `swarm_config.py` blueprint):

```
GET    /api/predictions/swarm-config
       → { agents: [{key, name, description, default, current, min, max}], customized: bool }

PUT    /api/predictions/swarm-config
       body: { weights: {"statistical": 2.0, ...} }     # validated & clamped
       → same shape as GET

DELETE /api/predictions/swarm-config                    # reset to defaults
```

**Wiring into predictions:**

- `POST /api/predictions/match` and `/tournament` load the caller's saved
  weights and pass them to the orchestrator.
- Both endpoints also accept an optional `agent_weights` body field as a
  **per-request override** (session-only experimentation from the Predict
  page without saving).
- `MatchPrediction.to_dict()` gains `weights_used` so the UI can display
  exactly what produced the numbers (transparency + reproducibility).

**Interaction with existing behavior:**

- MC-fallback tournament matches are unaffected (no agents involved).
- The played-matches-are-official logic (July fix) is unaffected — weights
  only apply to matches still being predicted.
- Billing hook (optional, decide later): gate `PUT` behind a plan flag the
  same way `includes_video_analysis` works today; free users see the sliders
  read-only with an upgrade prompt.

### Frontend — "Agent Weights" tab

- One slider row per agent: name, one-line description, slider `0.0–3.0`
  step `0.1`, numeric value, a tick mark at the default, and a computed
  **relative influence** bar (`weight / Σ weights`) so users see the ensemble
  share, not just the raw number.
- `Save`, `Reset to defaults`, and a dirty-state indicator; success/error
  toasts follow the AdminSettingsView pattern.
- On the Predict page: a compact "using custom weights" chip linking to the
  Swarm Lab when the user has customized weights.

---

## Part 2 — Knowledge graph visualization

### Current state

- `ZepFootballTools` already wraps Zep search and has `fetch_all_nodes` /
  `fetch_all_edges` helpers; agents consume text summaries only.
- `GET /api/predictions/graph/status` exists (admin). No graph data endpoint.

### Design

**Backend** — new endpoint:

```
GET /api/predictions/graph/data?team=<name>&limit=<n>
→ {
    mode: "zep_graph" | "static_fallback",
    nodes: [{ id, label, type: "team"|"group"|"competition"|"style", summary }],
    edges: [{ id, source, target, name, fact }],
    counts: { nodes, edges },
    built_at: iso8601
  }
```

- Zep mode: reuse `fetch_all_nodes`/`fetch_all_edges`; map Zep node labels to
  the `type` enum; cap payload (~500 nodes / ~2000 edges); **cache in-process
  with a 15-min TTL** — the graph changes rarely and Zep calls cost money.
- `team` param returns an ego-graph (that node + 1-hop neighbours) for
  focused exploration; no param returns the full capped graph.
- **Static fallback** (Zep not configured): synthesize the same shape from
  `TEAM_STATIC_DATA` + `WC2026_GROUPS` + `WC2026_RESULTS` — team nodes,
  group nodes, `PLAYS_IN_GROUP` edges, `BEAT`/`DREW_WITH` edges from real
  results, `HAS_STYLE` edges. The feature demos fully without a Zep key,
  consistent with how `ZepFootballTools` degrades everywhere else.

**Frontend — "Knowledge Graph" tab:**

- New dependency: **`d3-force` only** (~11 kB gz, tree-shakeable). No
  cytoscape/vis-network — too heavy for one view. Rendering is plain SVG
  driven by the simulation; zoom/pan via viewBox transform.
- Nodes colored by `type` (team=accent, group=muted, style=secondary), sized
  by degree. Drag to pin; hover an edge shows its `fact` text in a tooltip.
- Click a node → side panel with its summary and related facts (from the
  already-fetched edges — no extra API call).
- Controls: search-to-focus (jumps to the ego-graph via `?team=`), type
  filter chips, a "mode" badge (live Zep graph vs static fallback), and a
  legend. Empty/error/loading states follow the TournamentView tab pattern.
- Accessibility: the node list is also rendered as a visually-hidden,
  keyboard-navigable list; the SVG is `aria-hidden` with an `aria-live`
  summary of the selection.

---

## New workspace area

- Route: `/:locale(en|es)/competitions/:competitionEditionSlug/swarm`
  → `SwarmLabView.vue`, `meta: { requiresAuth: true, competitionWorkspace: true }`.
- `navigation.js`: add `{ key: 'swarm', capability: 'predictions', labelKey: 'navigation.workspace.swarm' }`.
- View structure mirrors `TournamentView.vue`: `AtlasPageHeader` + accessible
  tablist with two tabs (`weights`, `graph`), atlas design tokens throughout.
- i18n: new `swarmLab.*` + `navigation.workspace.swarm` keys in **both**
  `en` and `es` locale files (agent descriptions included).

## Files touched

Backend:
- `app/services/agents/weights.py` (new) — registry, `resolve_weights`
- `app/services/agents/aggregator_agent.py` — accept weights param, drop hardcoded dict
- `app/services/swarm_orchestrator.py` — `agent_weights` passthrough
- `app/api/predictions.py` (or new blueprint) — swarm-config CRUD, graph/data, weight loading in match/tournament
- `app/models/` + Alembic migration — `user_swarm_preferences`
- `app/services/zep_football_tools.py` — expose `get_graph_data()` w/ cache + static fallback
- tests: weights resolution, config API (auth, validation, clamping), graph data both modes

Frontend:
- `src/views/SwarmLabView.vue` (+ `.test.js`) — tabs shell
- `src/components/swarm/AgentWeightsPanel.vue`, `KnowledgeGraphPanel.vue` (+ tests)
- `src/router/index.js`, `src/router/workspace.js`, `src/competition/navigation.js`
- `src/i18n/locales/en*`, `es*`
- `package.json` — add `d3-force`

## Rollout plan

| Phase | Scope | Notes |
|---|---|---|
| 1 | Weights backend (registry, aggregator refactor, API, migration) | Ships value even without UI (API users) |
| 2 | Swarm Lab view + Agent Weights tab | Feature-complete for weights |
| 3 | Graph data endpoint + static fallback | Independent of 1–2 |
| 4 | Knowledge Graph tab | Depends on 3 |

Estimated effort: phases 1–2 ≈ one focused day; 3–4 ≈ one more.

## Open questions

1. Premium gating: are custom weights free, or a paid-plan feature?
2. Should muted (weight 0) agents be skipped entirely (faster, cheaper) or
   still run for display? Draft assumes: run but exclude from ensemble.
3. Graph tab visible to signed-out users as a marketing surface (read-only,
   static fallback), or auth-only like the rest of the workspace?

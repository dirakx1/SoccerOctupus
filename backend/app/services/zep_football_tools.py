"""
Zep Football Tools
==================
Mirrors MiroFish's ZepToolsService — wraps the Zep graph search API so
that prediction agents can query the knowledge graph instead of reading
from a static Python dictionary.

Three core retrieval patterns (matching MiroFish's toolset):
  search_facts(query)      — semantic search across all graph edges/facts
  get_team_context(team)   — full node + related edges for one team
  get_match_context(h, a)  — combined search for a specific fixture

Falls back to the static dataset when Zep is not configured, so the
system stays runnable without a ZEP_API_KEY.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger
from .data_collectors.sofascore_collector import TEAM_STATIC_DATA

logger = get_logger("fifaoctopus.zep_tools")


# ---------------------------------------------------------------------------
# Result dataclasses (same shape as MiroFish's SearchResult / InsightForgeResult)
# ---------------------------------------------------------------------------

@dataclass
class FootballFact:
    fact: str
    source_team: str = ""
    related_team: str = ""
    fact_type: str = ""

    def to_text(self) -> str:
        return self.fact


@dataclass
class TeamContext:
    team_name: str
    facts: List[FootballFact] = field(default_factory=list)
    summary: str = ""
    relationships: List[str] = field(default_factory=list)   # e.g. "France BEAT Morocco"

    def to_text(self) -> str:
        parts = [f"Team: {self.team_name}"]
        if self.summary:
            parts.append(f"Summary: {self.summary}")
        if self.facts:
            parts.append("Facts:")
            for f in self.facts[:10]:
                parts.append(f"  • {f.fact}")
        if self.relationships:
            parts.append("Relationships:")
            for r in self.relationships[:8]:
                parts.append(f"  → {r}")
        return "\n".join(parts)


@dataclass
class MatchContext:
    home_team: str
    away_team: str
    home_facts: List[FootballFact] = field(default_factory=list)
    away_facts: List[FootballFact] = field(default_factory=list)
    h2h_facts: List[FootballFact] = field(default_factory=list)

    def to_text(self) -> str:
        parts = [f"Match context: {self.home_team} (home) vs {self.away_team} (away)"]
        if self.h2h_facts:
            parts.append("\nHead-to-head:")
            for f in self.h2h_facts[:5]:
                parts.append(f"  • {f.fact}")
        if self.home_facts:
            parts.append(f"\n{self.home_team}:")
            for f in self.home_facts[:5]:
                parts.append(f"  • {f.fact}")
        if self.away_facts:
            parts.append(f"\n{self.away_team}:")
            for f in self.away_facts[:5]:
                parts.append(f"  • {f.fact}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main tools service
# ---------------------------------------------------------------------------

class ZepFootballTools:
    """
    Provides Zep-backed knowledge retrieval to all prediction agents.

    When an API key and graph_id are provided, queries use Zep's
    hybrid semantic+BM25 search over the football knowledge graph.

    When Zep is unavailable the fallback methods return structured text
    derived from the static TEAM_STATIC_DATA dict — identical to what
    agents used before, but wrapped in the same interface so agents need
    no branching logic.
    """

    MAX_RETRIES = 2
    RETRY_DELAY = 1.5

    def __init__(
        self,
        graph_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.graph_id = graph_id or ""
        self.api_key = api_key or ""
        self._zep = None

        if self.api_key and self.graph_id:
            try:
                from zep_cloud.client import Zep
                self._zep = Zep(api_key=self.api_key)
                logger.info(f"ZepFootballTools: live graph mode (graph_id={self.graph_id})")
            except Exception as exc:
                logger.warning(f"Zep init failed — falling back to static data: {exc}")
        else:
            logger.info("ZepFootballTools: static data fallback mode (no Zep API key/graph ID)")

    @property
    def has_graph(self) -> bool:
        return self._zep is not None and bool(self.graph_id)

    # ------------------------------------------------------------------
    # Public retrieval methods (used by agents)
    # ------------------------------------------------------------------

    def search_facts(self, query: str, limit: int = 10) -> List[FootballFact]:
        """
        Semantic search across all graph facts.
        Mirrors MiroFish's ZepToolsService.search_graph() / quick_search().
        """
        if self.has_graph:
            return self._zep_search(query, limit)
        return self._static_search(query, limit)

    def get_team_context(self, team_name: str) -> TeamContext:
        """
        Returns all known facts about one team.
        Mirrors MiroFish's get_entity_summary().
        """
        if self.has_graph:
            return self._zep_team_context(team_name)
        return self._static_team_context(team_name)

    def get_match_context(self, home: str, away: str) -> MatchContext:
        """
        Returns combined knowledge for a specific fixture.
        Mirrors MiroFish's InsightForge multi-sub-query pattern.
        """
        if self.has_graph:
            return self._zep_match_context(home, away)
        return self._static_match_context(home, away)

    # ------------------------------------------------------------------
    # Zep-backed implementations
    # ------------------------------------------------------------------

    def _zep_search(self, query: str, limit: int) -> List[FootballFact]:
        def _do():
            resp = self._zep.graph.search(
                graph_id=self.graph_id,
                query=query,
                limit=limit,
                scope="edges",
            )
            results = getattr(resp, "edges", None) or getattr(resp, "results", []) or []
            facts = []
            for edge in results:
                fact_text = getattr(edge, "fact", "") or getattr(edge, "name", "")
                if fact_text:
                    facts.append(FootballFact(
                        fact=fact_text,
                        fact_type=getattr(edge, "name", ""),
                    ))
            return facts

        try:
            return self._with_retry(_do, f"search:{query[:30]}")
        except Exception as exc:
            logger.warning(f"Zep search failed — static fallback: {exc}")
            return self._static_search(query, limit)

    def _zep_team_context(self, team_name: str) -> TeamContext:
        """Fetch node summary + related edges from Zep."""
        try:
            # Search for the team node
            from ..utils.zep_paging import fetch_all_nodes, fetch_all_edges
            nodes = fetch_all_nodes(self._zep, self.graph_id)
            team_node = next(
                (n for n in nodes if team_name.lower() in (n.name or "").lower()),
                None,
            )
            if not team_node:
                return self._static_team_context(team_name)

            # Get related edges
            all_edges = fetch_all_edges(self._zep, self.graph_id)
            related = [
                e for e in all_edges
                if e.source_node_uuid == team_node.uuid_
                or e.target_node_uuid == team_node.uuid_
            ]
            facts = [
                FootballFact(fact=e.fact or e.name or "", fact_type=e.name or "")
                for e in related if e.fact or e.name
            ]
            relationships = [
                e.fact for e in related if e.fact
            ]
            return TeamContext(
                team_name=team_name,
                facts=facts,
                summary=team_node.summary or "",
                relationships=relationships[:10],
            )
        except Exception as exc:
            logger.warning(f"Zep team context failed for {team_name}: {exc}")
            return self._static_team_context(team_name)

    def _zep_match_context(self, home: str, away: str) -> MatchContext:
        """Multi-query match context — mirrors MiroFish's InsightForge sub-query pattern."""
        queries = [
            f"{home} football statistics form goals",
            f"{away} football statistics form goals",
            f"{home} vs {away} head to head comparison",
            f"{home} tactical style playing system",
            f"{away} tactical style playing system",
        ]
        all_facts: List[FootballFact] = []
        for q in queries:
            all_facts.extend(self._zep_search(q, limit=4))
            time.sleep(0.1)

        home_facts = [f for f in all_facts if home.lower() in f.fact.lower()]
        away_facts = [f for f in all_facts if away.lower() in f.fact.lower()]
        h2h_facts = [
            f for f in all_facts
            if home.lower() in f.fact.lower() and away.lower() in f.fact.lower()
        ]
        return MatchContext(
            home_team=home,
            away_team=away,
            home_facts=home_facts[:6],
            away_facts=away_facts[:6],
            h2h_facts=h2h_facts[:4],
        )

    # ------------------------------------------------------------------
    # Static-data fallback implementations
    # ------------------------------------------------------------------

    def _static_search(self, query: str, limit: int) -> List[FootballFact]:
        """Keyword match against static team data."""
        q = query.lower()
        results = []
        for team, d in TEAM_STATIC_DATA.items():
            if team.lower() in q or q in team.lower():
                results.append(FootballFact(
                    fact=_team_summary_sentence(team, d),
                    source_team=team,
                    fact_type="team_profile",
                ))
        # Also surface any team whose style/confederation matches
        for team, d in TEAM_STATIC_DATA.items():
            style = d.get("style", "")
            if style and style in q:
                results.append(FootballFact(
                    fact=f"{team} plays a {style} system (ELO {d['elo']}, attack {d['att']}/100)",
                    source_team=team,
                    fact_type="tactical",
                ))
        return results[:limit] if results else [
            FootballFact(
                fact=f"Query '{query}' — no direct match in static dataset.",
                fact_type="no_result",
            )
        ]

    def _static_team_context(self, team_name: str) -> TeamContext:
        d = TEAM_STATIC_DATA.get(team_name, {})
        if not d:
            return TeamContext(team_name=team_name, summary="Unknown team")

        facts = [
            FootballFact(fact=_team_summary_sentence(team_name, d), source_team=team_name),
            FootballFact(fact=f"{team_name} plays a {d.get('style','balanced')} tactical system.", source_team=team_name),
            FootballFact(fact=f"{team_name} form: {d.get('form',15)}/30 pts in last 10 matches.", source_team=team_name),
            FootballFact(fact=f"{team_name} averages {d.get('gf',1.2)} goals scored and {d.get('ga',1.2)} conceded per match.", source_team=team_name),
        ]
        from .data_collectors.sofascore_collector import SofaScoreCollector
        h2h = SofaScoreCollector().get_head_to_head(team_name, "Average")
        relationships = [
            f"ELO {d.get('elo',1800)} — historical win rate vs average opponent: {h2h.get('a_historical_win_rate',0.5):.0%}"
        ]
        return TeamContext(
            team_name=team_name,
            facts=facts,
            summary=_team_summary_sentence(team_name, d),
            relationships=relationships,
        )

    def _static_match_context(self, home: str, away: str) -> MatchContext:
        from .data_collectors.sofascore_collector import SofaScoreCollector
        collector = SofaScoreCollector()
        h2h = collector.get_head_to_head(home, away)

        home_facts = [
            FootballFact(
                fact=_team_summary_sentence(home, TEAM_STATIC_DATA.get(home, {})),
                source_team=home,
            )
        ]
        away_facts = [
            FootballFact(
                fact=_team_summary_sentence(away, TEAM_STATIC_DATA.get(away, {})),
                source_team=away,
            )
        ]
        h2h_facts = [
            FootballFact(
                fact=(
                    f"{home} vs {away}: Elo gap {h2h['elo_diff']:+.0f} points. "
                    f"Historical win rate: {home} {h2h['a_historical_win_rate']:.0%} / "
                    f"{away} {h2h['b_historical_win_rate']:.0%}."
                ),
                source_team=home,
                related_team=away,
                fact_type="h2h",
            )
        ]
        return MatchContext(
            home_team=home, away_team=away,
            home_facts=home_facts,
            away_facts=away_facts,
            h2h_facts=h2h_facts,
        )

    # ------------------------------------------------------------------
    # Graph visualization data
    # ------------------------------------------------------------------

    MAX_GRAPH_NODES = 500
    MAX_GRAPH_EDGES = 2000
    GRAPH_CACHE_TTL = 900  # seconds — the graph changes rarely, Zep calls cost

    def get_graph_data(self, team: Optional[str] = None) -> Dict[str, Any]:
        """
        Nodes + edges for the frontend knowledge-graph explorer.

        Returns {mode, nodes, edges, counts, built_at}. With *team*, returns
        the ego-graph (that node and its 1-hop neighbourhood). Full-graph
        payloads are cached in-process for GRAPH_CACHE_TTL seconds.
        """
        full = self._graph_data_cached()
        if not team:
            return full

        needle = team.lower()
        seed_ids = {
            n["id"] for n in full["nodes"]
            if needle in n["label"].lower()
        }
        if not seed_ids:
            return {**full, "nodes": [], "edges": [], "counts": {"nodes": 0, "edges": 0}}

        edges = [
            e for e in full["edges"]
            if e["source"] in seed_ids or e["target"] in seed_ids
        ]
        keep = set(seed_ids)
        for e in edges:
            keep.add(e["source"])
            keep.add(e["target"])
        nodes = [n for n in full["nodes"] if n["id"] in keep]
        return {
            **full,
            "nodes": nodes,
            "edges": edges,
            "counts": {"nodes": len(nodes), "edges": len(edges)},
        }

    def _graph_data_cached(self) -> Dict[str, Any]:
        cache_key = f"{self.graph_id or 'static'}"
        cached = _GRAPH_CACHE.get(cache_key)
        if cached and time.time() - cached["at"] < self.GRAPH_CACHE_TTL:
            return cached["data"]

        if self.has_graph:
            try:
                data = self._zep_graph_data()
            except Exception as exc:
                logger.warning(f"Zep graph data failed — static fallback: {exc}")
                data = self._static_graph_data()
        else:
            data = self._static_graph_data()

        _GRAPH_CACHE[cache_key] = {"at": time.time(), "data": data}
        return data

    def _zep_graph_data(self) -> Dict[str, Any]:
        from ..utils.zep_paging import fetch_all_nodes, fetch_all_edges
        from datetime import datetime, timezone

        raw_nodes = fetch_all_nodes(self._zep, self.graph_id)[: self.MAX_GRAPH_NODES]
        node_ids = set()
        nodes = []
        for n in raw_nodes:
            uuid_ = getattr(n, "uuid_", None) or getattr(n, "uuid", None)
            name = getattr(n, "name", "") or ""
            if not uuid_ or not name:
                continue
            node_ids.add(uuid_)
            nodes.append({
                "id": uuid_,
                "label": name,
                "type": _node_type(name, getattr(n, "labels", None)),
                "summary": (getattr(n, "summary", "") or "")[:400],
            })

        raw_edges = fetch_all_edges(self._zep, self.graph_id)[: self.MAX_GRAPH_EDGES]
        edges = []
        for e in raw_edges:
            src = getattr(e, "source_node_uuid", None)
            tgt = getattr(e, "target_node_uuid", None)
            if src not in node_ids or tgt not in node_ids:
                continue
            edges.append({
                "id": getattr(e, "uuid_", None) or getattr(e, "uuid", "") or f"{src}-{tgt}",
                "source": src,
                "target": tgt,
                "name": getattr(e, "name", "") or "RELATED_TO",
                "fact": (getattr(e, "fact", "") or "")[:300],
            })

        return {
            "mode": "zep_graph",
            "nodes": nodes,
            "edges": edges,
            "counts": {"nodes": len(nodes), "edges": len(edges)},
            "built_at": datetime.now(timezone.utc).isoformat(),
        }

    def _static_graph_data(self) -> Dict[str, Any]:
        """
        Synthesize the same graph shape from static data + real results so
        the explorer works without a Zep key.
        """
        from datetime import datetime, timezone
        from .tournament_simulator import WC2026_GROUPS
        from .data_collectors.live_results import WC2026_RESULTS

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        def team_id(name: str) -> str:
            return f"team:{name}"

        team_names = set()
        for letter, teams in WC2026_GROUPS.items():
            gid = f"group:{letter}"
            nodes.append({
                "id": gid,
                "label": f"Group {letter}",
                "type": "group",
                "summary": f"FIFA World Cup 2026 Group {letter}: {', '.join(teams)}.",
            })
            for t in teams:
                team_names.add(t)
                d = TEAM_STATIC_DATA.get(t, {})
                nodes.append({
                    "id": team_id(t),
                    "label": t,
                    "type": "team",
                    "summary": _team_summary_sentence(t, d),
                })
                edges.append({
                    "id": f"in:{t}",
                    "source": team_id(t),
                    "target": gid,
                    "name": "PLAYS_IN_GROUP",
                    "fact": f"{t} plays in World Cup 2026 Group {letter}.",
                })

        # Tactical style nodes
        styles = {}
        for t in sorted(team_names):
            style = TEAM_STATIC_DATA.get(t, {}).get("style")
            if not style:
                continue
            sid = f"style:{style}"
            if sid not in styles:
                styles[sid] = True
                nodes.append({
                    "id": sid,
                    "label": style,
                    "type": "style",
                    "summary": f"Teams playing a {style} tactical system.",
                })
            edges.append({
                "id": f"style:{t}",
                "source": team_id(t),
                "target": sid,
                "name": "HAS_STYLE",
                "fact": f"{t} plays a {style} system.",
            })

        # Played-match edges from official results
        for i, m in enumerate(WC2026_RESULTS):
            home, away = m["home"], m["away"]
            if home not in team_names or away not in team_names:
                continue
            hg, ag = m["home_goals"], m["away_goals"]
            winner = m.get("winner")
            if hg == ag and not winner:
                name = "DREW_WITH"
                src, tgt = home, away
                fact = f"{home} drew {hg}-{ag} with {away} on {m['date']}."
            else:
                w = winner or (home if hg > ag else away)
                loser = away if w == home else home
                name = "BEAT"
                src, tgt = w, loser
                pens = " (decided after extra time / penalties)" if hg == ag else ""
                fact = f"{w} beat {loser} {max(hg, ag)}-{min(hg, ag)} on {m['date']}{pens}."
            edges.append({
                "id": f"match:{i}",
                "source": team_id(src),
                "target": team_id(tgt),
                "name": name,
                "fact": fact,
            })

        return {
            "mode": "static_fallback",
            "nodes": nodes[: self.MAX_GRAPH_NODES],
            "edges": edges[: self.MAX_GRAPH_EDGES],
            "counts": {"nodes": len(nodes), "edges": len(edges)},
            "built_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Retry wrapper (same pattern as MiroFish's _call_with_retry)
    # ------------------------------------------------------------------

    def _with_retry(self, func, label: str):
        delay = self.RETRY_DELAY
        last_exc = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return func()
            except Exception as exc:
                last_exc = exc
                logger.warning(f"Zep call '{label}' attempt {attempt+1} failed: {exc}")
                time.sleep(delay)
                delay *= 2
        raise last_exc


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

# Module-level cache for graph visualization payloads ({key: {at, data}}).
_GRAPH_CACHE: Dict[str, Dict[str, Any]] = {}


def _node_type(name: str, labels: Optional[List[str]]) -> str:
    """Map a Zep node to the frontend type enum."""
    for label in labels or []:
        low = str(label).lower()
        if "team" in low:
            return "team"
        if "group" in low:
            return "group"
        if "competition" in low:
            return "competition"
        if "style" in low or "tactic" in low:
            return "style"
    if name in TEAM_STATIC_DATA:
        return "team"
    if name.lower().startswith("group "):
        return "group"
    if "world cup" in name.lower():
        return "competition"
    return "entity"


def _team_summary_sentence(team: str, d: Dict[str, Any]) -> str:
    if not d:
        return f"{team} — no data available."
    return (
        f"{team}: ELO {d.get('elo','?')}, FIFA #{d.get('rank','?')}, "
        f"{d.get('style','balanced')} style, "
        f"attack {d.get('att','?')}/100, defence {d.get('def','?')}/100, "
        f"form {d.get('form','?')}/30 pts, "
        f"{d.get('gf','?')} goals/game scored, {d.get('ga','?')} conceded."
    )

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

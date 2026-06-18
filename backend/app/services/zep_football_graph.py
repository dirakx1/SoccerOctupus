"""
Zep Football Knowledge Graph Builder
=====================================
Mirrors MiroFish's GraphBuilderService exactly, but seeds the graph with
football-domain knowledge instead of uploaded documents.

The graph stores:
  Nodes  — NationalTeam, Competition, Coach, Group
  Edges  — BEAT, DREW_WITH, LOST_TO, PLAYS_IN_GROUP, RANKED_ABOVE,
            HAS_STYLE, QUALIFIED_FOR

Agents query this graph (via ZepFootballTools) instead of reading from a
static Python dict — the same way MiroFish's ReportAgent queries Zep instead
of operating on raw uploaded text.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger
from .data_collectors.sofascore_collector import TEAM_STATIC_DATA
from .tournament_simulator import WC2026_GROUPS

logger = get_logger("fifaoctopus.zep_graph")


def _require_zep():
    try:
        from zep_cloud.client import Zep
        from zep_cloud import EpisodeData
        return Zep, EpisodeData
    except ImportError as exc:
        raise RuntimeError(
            "zep-cloud is not installed. Run: pip install zep-cloud"
        ) from exc


# ---------------------------------------------------------------------------
# Episode text builders  (these become the "seed documents" Zep ingests)
# ---------------------------------------------------------------------------

def _team_episode(name: str, d: Dict[str, Any]) -> str:
    """Produce a rich natural-language paragraph about one team."""
    return (
        f"{name} is a national football team competing in FIFA World Cup 2026. "
        f"They belong to the {d.get('confederation', 'unknown')} confederation and are ranked "
        f"#{d.get('rank', '?')} in the FIFA World Rankings. "
        f"Their World Football Elo rating is {d.get('elo', '?')}. "
        f"Tactically they play a {d.get('style', 'balanced')} system. "
        f"In recent matches they average {d.get('gf', '?')} goals scored and "
        f"{d.get('ga', '?')} goals conceded per game. "
        f"Their attack rating is {d.get('att', '?')}/100 and defensive rating is "
        f"{d.get('def', '?')}/100. "
        f"Over their last 10 official matches they have accumulated {d.get('form', '?')} "
        f"points out of a possible 30."
    )


def _group_episode(group_letter: str, teams: List[str]) -> str:
    ranked = sorted(teams, key=lambda t: -TEAM_STATIC_DATA.get(t, {}).get("elo", 0))
    return (
        f"FIFA World Cup 2026 Group {group_letter} contains four teams: "
        f"{', '.join(teams)}. "
        f"By Elo rating the strongest team in the group is {ranked[0]} "
        f"(Elo {TEAM_STATIC_DATA.get(ranked[0], {}).get('elo', '?')}), "
        f"followed by {ranked[1]} "
        f"(Elo {TEAM_STATIC_DATA.get(ranked[1], {}).get('elo', '?')}). "
        f"The group stage allows draws — each team plays the other three once, "
        f"with the top two teams and the eight best third-place teams advancing "
        f"to the Round of 32."
    )


def _h2h_episode(team_a: str, team_b: str) -> str:
    da = TEAM_STATIC_DATA.get(team_a, {"elo": 1800})
    db = TEAM_STATIC_DATA.get(team_b, {"elo": 1800})
    elo_diff = da["elo"] - db["elo"]
    win_rate = round(1 / (1 + 10 ** (-elo_diff / 400)), 2)
    stronger = team_a if elo_diff > 0 else team_b
    weaker = team_b if elo_diff > 0 else team_a
    return (
        f"Head-to-head context: {team_a} vs {team_b}. "
        f"Elo difference is {abs(elo_diff)} points in favour of {stronger}. "
        f"Based on Elo ratings, {stronger} has a historical win rate of "
        f"{max(win_rate, 1-win_rate):.0%} against {weaker}. "
        f"{team_a}'s playing style is {da.get('style', 'balanced')} while "
        f"{team_b}'s is {db.get('style', 'balanced')}."
    )


def _tactical_episode(name: str, d: Dict[str, Any]) -> str:
    style = d.get("style", "balanced")
    strengths = {
        "high-press": "pressing high up the pitch, winning the ball in dangerous areas and transitioning quickly",
        "counter-attack": "absorbing pressure and exploiting space in behind the opposition defence",
        "tiki-taka": "maintaining possession through short passing combinations to control tempo",
        "defensive": "compact low-block organisation, limiting space and counter-attacking on the break",
        "gegenpressing": "immediate ball recovery after losing possession in the final third",
        "possession": "dictating the game through patient build-up and positional play",
        "balanced": "adapting fluidly between phases of play",
    }
    desc = strengths.get(style, "a flexible approach")
    return (
        f"Tactical analysis of {name}: Their primary system is {style}, "
        f"characterised by {desc}. "
        f"With an attack rating of {d.get('att', 65)}/100 and a defence rating of "
        f"{d.get('def', 65)}/100, they are "
        f"{'stronger in attack than defence' if d.get('att', 65) > d.get('def', 65) else 'stronger in defence than attack' if d.get('def', 65) > d.get('att', 65) else 'balanced across both phases'}. "
        f"Their Elo of {d.get('elo', 1800)} places them "
        f"{'among the tournament favourites' if d.get('elo', 1800) >= 2000 else 'in the mid-tier' if d.get('elo', 1800) >= 1870 else 'among the underdogs'}."
    )


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

class ZepFootballGraphBuilder:
    """
    Builds a Zep standalone graph from football seed data.

    Mirrors MiroFish's GraphBuilderService:
      1. Create graph
      2. Set ontology
      3. Ingest text episodes (team profiles, group context, H2H facts, tactics)
      4. Wait for Zep to process all episodes into nodes + edges
      5. Return graph_id for agents to query
    """

    GRAPH_NAME = "FifaOctopus WC2026"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ""
        if not self.api_key:
            raise ValueError(
                "Zep API key is not set. Add it in admin settings."
            )
        Zep, _ = _require_zep()
        self.client = Zep(api_key=self.api_key)

    # ------------------------------------------------------------------

    def build(self, progress_callback=None) -> str:
        """
        Build the full WC2026 knowledge graph and return its graph_id.

        Args:
            progress_callback: optional callable(pct: int, msg: str)
        """
        def _cb(pct: int, msg: str):
            logger.info(f"[{pct:3d}%] {msg}")
            if progress_callback:
                progress_callback(pct, msg)

        _cb(0, "Creating Zep graph…")
        graph_id = self._create_graph()
        _cb(5, f"Graph created: {graph_id}")

        _cb(8, "Setting football ontology…")
        self._set_ontology(graph_id)

        episodes = self._build_episodes()
        total = len(episodes)
        _cb(12, f"Prepared {total} knowledge episodes")

        episode_uuids = self._ingest_episodes(graph_id, episodes, _cb)

        _cb(75, f"Waiting for Zep to process {len(episode_uuids)} episodes…")
        self._wait_for_processing(episode_uuids, _cb)

        _cb(100, f"Graph ready. graph_id={graph_id}")
        return graph_id

    # ------------------------------------------------------------------

    def _create_graph(self) -> str:
        gid = f"fifaoctopus_{uuid.uuid4().hex[:16]}"
        self.client.graph.create(
            graph_id=gid,
            name=self.GRAPH_NAME,
            description="FIFA World Cup 2026 football knowledge graph for FifaOctopus predictions",
        )
        return gid

    def _set_ontology(self, graph_id: str):
        """Define entity and edge types — same pattern as MiroFish's GraphBuilderService.set_ontology."""
        try:
            import warnings
            from typing import Optional as Opt
            from pydantic import Field
            from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel
            from zep_cloud import EntityEdgeSourceTarget

            warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

            # --- Entity types ---
            NationalTeam = type("NationalTeam", (EntityModel,), {
                "__doc__": "A national football team",
                "__annotations__": {
                    "confederation": Opt[EntityText],
                    "elo_rating": Opt[EntityText],
                    "fifa_ranking": Opt[EntityText],
                    "playing_style": Opt[EntityText],
                    "form_points": Opt[EntityText],
                },
                "confederation": Field(description="FIFA confederation (UEFA, CONMEBOL, etc.)", default=None),
                "elo_rating": Field(description="World Football Elo rating", default=None),
                "fifa_ranking": Field(description="Current FIFA world ranking number", default=None),
                "playing_style": Field(description="Tactical playing style", default=None),
                "form_points": Field(description="Points from last 10 official matches out of 30", default=None),
            })

            Group = type("Group", (EntityModel,), {
                "__doc__": "A WC2026 group (A through L)",
                "__annotations__": {"group_letter": Opt[EntityText]},
                "group_letter": Field(description="Group letter A-L", default=None),
            })

            # --- Edge types ---
            Beat = type("Beat", (EdgeModel,), {
                "__doc__": "Team A beat Team B",
                "__annotations__": {"competition": Opt[str], "score": Opt[str]},
                "competition": Field(description="Competition name", default=None),
                "score": Field(description="Final score", default=None),
            })
            PlaysInGroup = type("PlaysInGroup", (EdgeModel,), {
                "__doc__": "Team is assigned to a WC group",
                "__annotations__": {"seeding": Opt[str]},
                "seeding": Field(description="Pot/seeding", default=None),
            })
            RankedAbove = type("RankedAbove", (EdgeModel,), {
                "__doc__": "Team A is ranked higher than Team B by Elo",
                "__annotations__": {"elo_diff": Opt[str]},
                "elo_diff": Field(description="Elo rating difference", default=None),
            })

            self.client.graph.set_ontology(
                graph_ids=[graph_id],
                entities={"NationalTeam": NationalTeam, "Group": Group},
                edges={
                    "beat": (Beat, [EntityEdgeSourceTarget(source="NationalTeam", target="NationalTeam")]),
                    "plays_in_group": (PlaysInGroup, [EntityEdgeSourceTarget(source="NationalTeam", target="Group")]),
                    "ranked_above": (RankedAbove, [EntityEdgeSourceTarget(source="NationalTeam", target="NationalTeam")]),
                },
            )
            logger.info("Ontology set successfully")
        except Exception as exc:
            logger.warning(f"Ontology set failed (graph will still work without typed schema): {exc}")

    def _build_episodes(self) -> List[str]:
        """Build all text episodes — Zep will parse these into nodes and edges."""
        episodes: List[str] = []

        # 1. Team profiles (one episode per team)
        for name, data in TEAM_STATIC_DATA.items():
            data_with_conf = dict(data)
            # Infer confederation from name lookup
            conf = _infer_confederation(name)
            data_with_conf["confederation"] = conf
            episodes.append(_team_episode(name, data_with_conf))

        # 2. Tactical analysis (second pass for richer tactical context)
        for name, data in TEAM_STATIC_DATA.items():
            episodes.append(_tactical_episode(name, data))

        # 3. Group context
        for group_letter, teams in WC2026_GROUPS.items():
            episodes.append(_group_episode(group_letter, teams))

        # 4. H2H context for all group-stage matchups
        import itertools
        for group_letter, teams in WC2026_GROUPS.items():
            for team_a, team_b in itertools.combinations(teams, 2):
                episodes.append(_h2h_episode(team_a, team_b))

        # 5. Ranking comparisons for top teams
        top = sorted(TEAM_STATIC_DATA.items(), key=lambda x: -x[1]["elo"])[:20]
        for i, (t_a, _) in enumerate(top):
            for t_b, _ in top[i + 1:i + 4]:
                episodes.append(_h2h_episode(t_a, t_b))

        return episodes

    def _ingest_episodes(
        self,
        graph_id: str,
        episodes: List[str],
        cb,
        batch_size: int = 5,
    ) -> List[str]:
        """Send episodes to Zep in batches, return list of episode UUIDs."""
        _, EpisodeData = _require_zep()
        uuids: List[str] = []
        total = len(episodes)

        for i in range(0, total, batch_size):
            batch = episodes[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            pct = 12 + int((i / total) * 63)
            cb(pct, f"Ingesting batch {batch_num}/{total_batches} ({len(batch)} episodes)")

            try:
                result = self.client.graph.add_batch(
                    graph_id=graph_id,
                    episodes=[EpisodeData(data=ep, type="text") for ep in batch],
                )
                if result and isinstance(result, list):
                    for ep in result:
                        ep_uuid = getattr(ep, "uuid_", None) or getattr(ep, "uuid", None)
                        if ep_uuid:
                            uuids.append(ep_uuid)
                time.sleep(0.8)
            except Exception as exc:
                logger.warning(f"Batch {batch_num} failed: {exc}")

        return uuids

    def _wait_for_processing(
        self,
        episode_uuids: List[str],
        cb,
        timeout: int = 300,
    ):
        """Poll until all episodes are processed — same pattern as MiroFish."""
        if not episode_uuids:
            return
        pending = set(episode_uuids)
        start = time.time()
        completed = 0

        while pending and time.time() - start < timeout:
            for ep_uuid in list(pending):
                try:
                    ep = self.client.graph.episode.get(uuid_=ep_uuid)
                    if getattr(ep, "processed", False):
                        pending.discard(ep_uuid)
                        completed += 1
                except Exception:
                    pass

            elapsed = int(time.time() - start)
            pct = 75 + int(completed / len(episode_uuids) * 24)
            cb(pct, f"Processing: {completed}/{len(episode_uuids)} done ({len(pending)} pending, {elapsed}s)")

            if pending:
                time.sleep(4)


# ---------------------------------------------------------------------------
# Confederation lookup
# ---------------------------------------------------------------------------

_CONFEDERATION_MAP: Dict[str, str] = {
    # UEFA
    "France": "UEFA", "Spain": "UEFA", "England": "UEFA", "Germany": "UEFA",
    "Portugal": "UEFA", "Netherlands": "UEFA", "Italy": "UEFA", "Belgium": "UEFA",
    "Croatia": "UEFA", "Austria": "UEFA", "Switzerland": "UEFA", "Denmark": "UEFA",
    "Poland": "UEFA", "Serbia": "UEFA", "Turkey": "UEFA", "Hungary": "UEFA",
    "Czech Republic": "UEFA", "Romania": "UEFA", "Scotland": "UEFA", "Ukraine": "UEFA",
    "Slovakia": "UEFA", "Albania": "UEFA", "Slovenia": "UEFA", "Georgia": "UEFA",
    # CONMEBOL
    "Brazil": "CONMEBOL", "Argentina": "CONMEBOL", "Uruguay": "CONMEBOL",
    "Colombia": "CONMEBOL", "Ecuador": "CONMEBOL", "Paraguay": "CONMEBOL",
    "Chile": "CONMEBOL", "Peru": "CONMEBOL", "Bolivia": "CONMEBOL", "Venezuela": "CONMEBOL",
    # CAF
    "Morocco": "CAF", "Senegal": "CAF", "Nigeria": "CAF", "Egypt": "CAF",
    "Cameroon": "CAF", "Ivory Coast": "CAF", "Tunisia": "CAF", "Ghana": "CAF",
    "South Africa": "CAF", "Mali": "CAF", "Algeria": "CAF",
    # AFC
    "Japan": "AFC", "South Korea": "AFC", "Iran": "AFC", "Saudi Arabia": "AFC",
    "Australia": "AFC", "Qatar": "AFC", "Uzbekistan": "AFC", "Iraq": "AFC",
    # CONCACAF
    "USA": "CONCACAF", "Mexico": "CONCACAF", "Canada": "CONCACAF",
    "Jamaica": "CONCACAF", "Honduras": "CONCACAF", "Costa Rica": "CONCACAF",
    "Panama": "CONCACAF",
    # OFC
    "New Zealand": "OFC",
    # Unknown / placeholder
    "Indonesia": "AFC",
}


def _infer_confederation(team: str) -> str:
    return _CONFEDERATION_MAP.get(team, "FIFA")

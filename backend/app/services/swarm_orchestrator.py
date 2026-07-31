"""
Swarm Orchestrator
==================
Spawns all agents in parallel threads, each with access to a shared
ZepFootballTools instance — exactly mirroring how MiroFish's agents share
a Zep graph for knowledge retrieval.

Without Zep the system falls back transparently to static data.
"""

from __future__ import annotations

import concurrent.futures
from typing import Any, Dict, List, Optional

from ..models.match import AgentPrediction, MatchPrediction, MatchStage
from ..runtime_settings import RuntimeSettings
from ..utils.logger import get_logger
from .agents import (
    AggregatorAgent,
    FormAgent,
    LiveDataAgent,
    MarketSignalsAgent,
    SquadQualityAgent,
    StatisticalAgent,
    TacticalAgent,
    VideoAgent,
)
from .zep_football_tools import ZepFootballTools

logger = get_logger("fifaoctopus.swarm")


class SwarmOrchestrator:
    """
    Orchestrates the prediction swarm.

    Architecture mirrors MiroFish's SimulationManager:
      - ZepFootballTools is initialised once and shared across all agents
        (same as MiroFish sharing a single Zep client / graph_id)
      - Each agent runs in its own thread, querying Zep for knowledge
      - Results are aggregated with an optional LLM narrative synthesis
    """

    def __init__(
        self,
        settings: RuntimeSettings,
        llm_client=None,
        zep_tools: ZepFootballTools | None = None,
        include_video_analysis: bool = True,
        agent_weights: dict | None = None,
    ):
        self.settings = settings
        self.llm_client = llm_client
        # Sparse {agent_key: weight} overrides forwarded to the aggregator
        self.agent_weights = agent_weights

        # One shared Zep tools instance — all agents query the same graph
        # Falls back to static data automatically when DB-backed Zep settings are absent
        self.zep = zep_tools or _try_build_zep_tools(settings)

        if self.zep and self.zep.has_graph:
            logger.info("SwarmOrchestrator: Zep knowledge graph ACTIVE")
        else:
            logger.info("SwarmOrchestrator: Zep not configured — using static data fallback")

        # Build the swarm — every agent receives the shared zep_tools reference
        self.agents = [
            StatisticalAgent(zep_tools=self.zep),          # ELO + Poisson (SofaScore)
            FormAgent(zep_tools=self.zep),                 # last-10 form points
            TacticalAgent(llm_client=llm_client, zep_tools=self.zep),  # style matchup
            LiveDataAgent(zep_tools=self.zep),             # FotMob xG + FlashScore form
            MarketSignalsAgent(zep_tools=self.zep),        # 365Scores odds + Tiki-Taka AI
            SquadQualityAgent(settings=settings, zep_tools=self.zep),  # Opta player ratings + squad depth
        ]
        if include_video_analysis:
            self.agents.insert(1, VideoAgent(settings=settings))  # YouTube engagement
        self.aggregator = AggregatorAgent(llm_client=llm_client)

        logger.info(
            f"SwarmOrchestrator ready with {len(self.agents)} agents: "
            + ", ".join(a.name for a in self.agents)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict_match(
        self,
        home_team: str,
        away_team: str,
        stage: MatchStage = MatchStage.GROUP,
        group: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        progress_callback=None,
    ) -> MatchPrediction:
        """
        Run all agents in parallel and aggregate their predictions.

        Args:
            home_team:          Home side team name
            away_team:          Away side team name
            stage:              Tournament stage (affects narrative)
            group:              Group letter (for group stage)
            context:            Extra context forwarded to agents
            progress_callback:  Optional callable(stage, pct, msg)
        """
        ctx = context or {}
        ctx.update({"stage": stage.value, "group": group})

        if progress_callback:
            progress_callback("running", 0, f"Swarm starting for {home_team} vs {away_team}")

        agent_preds: List[AgentPrediction] = []
        errors: List[str] = []

        timeout = self.settings.swarm_timeout_seconds
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.settings.swarm_parallel_agents
        ) as executor:
            future_map = {
                executor.submit(agent.predict, home_team, away_team, ctx): agent
                for agent in self.agents
            }

            done_count = 0
            total = len(future_map)
            for future in concurrent.futures.as_completed(future_map, timeout=timeout):
                agent = future_map[future]
                done_count += 1
                pct = int(done_count / total * 80)
                try:
                    pred = future.result()
                    agent_preds.append(pred)
                    logger.info(
                        f"[{agent.name}] {home_team} {pred.home_win_prob:.0%} / "
                        f"Draw {pred.draw_prob:.0%} / {away_team} {pred.away_win_prob:.0%}"
                    )
                    if progress_callback:
                        progress_callback(
                            "running", pct,
                            f"{agent.name} done → {home_team} {pred.home_win_prob:.0%}"
                        )
                except Exception as exc:
                    err = f"{agent.name} failed: {exc}"
                    errors.append(err)
                    logger.warning(err)

        if not agent_preds:
            raise RuntimeError(
                f"All agents failed for {home_team} vs {away_team}: {errors}"
            )

        if progress_callback:
            progress_callback("aggregating", 85, "Aggregating swarm predictions…")

        result = self.aggregator.aggregate(
            home_team=home_team,
            away_team=away_team,
            stage=stage,
            group=group,
            agent_predictions=agent_preds,
            weights=self.agent_weights,
        )

        if progress_callback:
            progress_callback(
                "done", 100,
                f"Prediction complete: {result.outcome.value} ({result.overall_confidence:.0%} confidence)"
            )

        logger.info(
            f"FINAL {home_team} vs {away_team}: "
            f"HW={result.home_win_prob:.1%} D={result.draw_prob:.1%} AW={result.away_win_prob:.1%} "
            f"Score={result.most_likely_score}"
        )
        return result


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _try_build_zep_tools(settings: RuntimeSettings) -> ZepFootballTools:
    """
    Build ZepFootballTools using DB-backed Zep settings.
    Always returns a ZepFootballTools object; static fallback activates when
    credentials are absent.
    """
    return ZepFootballTools(api_key=settings.zep_api_key, graph_id=settings.zep_graph_id)

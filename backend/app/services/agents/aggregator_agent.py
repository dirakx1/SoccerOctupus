"""
Aggregator Agent
================
Combines predictions from all swarm agents using weighted averaging,
then calls the LLM to synthesise a human-readable consensus narrative.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ...models.match import AgentPrediction, MatchOutcome, MatchPrediction, MatchStage
from ...utils.llm_client import LLMClient
from ...utils.logger import get_logger

logger = get_logger("fifaoctopus.agent.aggregator")


AGGREGATE_SYSTEM_PROMPT = """\
You are FifaOctopus, an elite football prediction AI.
You receive a JSON array of predictions from specialised swarm agents
(statistical, video-intelligence, form, tactical) for a single FIFA World Cup match.
Your job:
1. Synthesise the agents' findings into one clear match narrative (3-4 sentences).
2. Identify the 3 most critical factors that will decide the match.
3. State the most likely scoreline.
Output ONLY a JSON object:
{
  "narrative": "...",
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "most_likely_score": "X-Y"
}"""


class AggregatorAgent:
    """Weighted ensemble + LLM narrative synthesis."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self._llm: Optional[LLMClient] = llm_client

    def aggregate(
        self,
        home_team: str,
        away_team: str,
        stage: MatchStage,
        group: Optional[str],
        agent_predictions: List[AgentPrediction],
    ) -> MatchPrediction:
        import uuid

        if not agent_predictions:
            raise ValueError("No agent predictions to aggregate")

        total_weight = sum(p.confidence for p in agent_predictions)  # confidence-weighted
        # Actually use agent weight * confidence for true weighting
        # We need access to agent weights; they are embedded in the prediction names — use fallback weights
        AGENT_WEIGHTS = {
            "Statistical Analysis Agent": 1.8,
            "Video Intelligence Agent": 1.0,
            "Recent Form Agent": 1.3,
            "Tactical Analysis Agent": 1.2,
            "Live Data Agent": 1.4,
            "Market Signals Agent": 0.8,
            "Squad Quality Agent": 1.1,
        }

        w_sum = 0.0
        hw_agg = dr_agg = aw_agg = 0.0
        xg_home = xg_away = 0.0

        for pred in agent_predictions:
            w = AGENT_WEIGHTS.get(pred.agent_name, 1.0) * pred.confidence
            w_sum += w
            hw_agg += pred.home_win_prob * w
            dr_agg += pred.draw_prob * w
            aw_agg += pred.away_win_prob * w
            xg_home += pred.predicted_home_goals * w
            xg_away += pred.predicted_away_goals * w

        hw_final = hw_agg / w_sum
        dr_final = dr_agg / w_sum
        aw_final = aw_agg / w_sum
        xg_home_final = xg_home / w_sum
        xg_away_final = xg_away / w_sum

        # Renormalise probabilities
        t = hw_final + dr_final + aw_final
        hw_final /= t
        dr_final /= t
        aw_final /= t

        outcome = (
            MatchOutcome.HOME_WIN if hw_final > dr_final and hw_final > aw_final
            else MatchOutcome.DRAW if dr_final >= aw_final and dr_final >= hw_final
            else MatchOutcome.AWAY_WIN
        )

        most_likely_score = f"{round(xg_home_final)}-{round(xg_away_final)}"
        overall_confidence = sum(p.confidence for p in agent_predictions) / len(agent_predictions)

        # LLM narrative
        narrative, key_factors = self._synthesise(
            home_team, away_team, agent_predictions, hw_final, dr_final, aw_final,
            most_likely_score
        )

        prediction_id = f"pred_{uuid.uuid4().hex[:10]}"
        return MatchPrediction(
            prediction_id=prediction_id,
            home_team=home_team,
            away_team=away_team,
            stage=stage,
            group=group,
            home_win_prob=round(hw_final, 3),
            draw_prob=round(dr_final, 3),
            away_win_prob=round(aw_final, 3),
            predicted_home_goals=round(xg_home_final, 2),
            predicted_away_goals=round(xg_away_final, 2),
            most_likely_score=most_likely_score,
            outcome=outcome,
            overall_confidence=round(overall_confidence, 3),
            agent_predictions=agent_predictions,
            swarm_consensus=narrative,
            key_factors=key_factors,
        )

    # ------------------------------------------------------------------

    def _synthesise(
        self,
        home: str,
        away: str,
        preds: List[AgentPrediction],
        hw: float,
        dr: float,
        aw: float,
        score: str,
    ):
        """Call LLM to generate narrative + key factors. Falls back gracefully."""
        if not self._llm:
            return self._fallback_narrative(home, away, hw, dr, aw, score, preds), \
                   self._fallback_factors(home, away, preds)

        payload = [
            {
                "agent": p.agent_name,
                "home_win_prob": p.home_win_prob,
                "draw_prob": p.draw_prob,
                "away_win_prob": p.away_win_prob,
                "reasoning": p.reasoning,
            }
            for p in preds
        ]
        try:
            result = self._llm.chat_json(
                messages=[
                    {"role": "system", "content": AGGREGATE_SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"Match: {home} (home) vs {away} (away)\n"
                        f"Aggregated probabilities: {home} win {hw:.1%} / Draw {dr:.1%} / {away} win {aw:.1%}\n"
                        f"Most likely score: {score}\n\n"
                        f"Agent predictions:\n{json.dumps(payload, indent=2)}"
                    )},
                ]
            )
            narrative = result.get("narrative", "")
            key_factors = result.get("key_factors", [])
            return narrative, key_factors
        except Exception as exc:
            logger.warning(f"LLM synthesis failed: {exc}. Using fallback.")
            return self._fallback_narrative(home, away, hw, dr, aw, score, preds), \
                   self._fallback_factors(home, away, preds)

    @staticmethod
    def _fallback_narrative(home, away, hw, dr, aw, score, preds):
        fav = home if hw > aw else (away if aw > hw else "neither side")
        conf = max(hw, dr, aw)
        return (
            f"The swarm of {len(preds)} specialised agents gives {home} a {hw:.1%} win probability, "
            f"with {dr:.1%} for a draw and {aw:.1%} for {away}. "
            f"{'Neither side holds a commanding edge' if conf < 0.45 else f'{fav} is the narrow favourite'}, "
            f"with a predicted scoreline of {score}."
        )

    @staticmethod
    def _fallback_factors(home, away, preds):
        factors = []
        stat_pred = next((p for p in preds if "Statistical" in p.agent_name), None)
        form_pred = next((p for p in preds if "Form" in p.agent_name), None)
        tact_pred = next((p for p in preds if "Tactical" in p.agent_name), None)
        if stat_pred:
            factors.append(f"ELO and SofaScore statistics favour {'home' if stat_pred.home_win_prob > stat_pred.away_win_prob else 'away'}")
        if form_pred:
            factors.append(f"Recent form: {'home side in better shape' if form_pred.home_win_prob > form_pred.away_win_prob else 'away side in better shape'}")
        if tact_pred:
            factors.append(f"Tactical style matchup: {tact_pred.reasoning[:80]}...")
        return factors or ["Statistical model", "Recent form", "Tactical analysis"]

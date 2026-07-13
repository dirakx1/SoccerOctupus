"""
Tournament Simulator
====================
Simulates the entire FIFA World Cup 2026 bracket.

Structure:
  - 48 teams, 12 groups of 4
  - Top 2 from each group + 8 best 3rd-place teams = 32 for Round of 32
  - Knockout: R32 → R16 → QF → SF → Final + 3rd place play-off
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..models.match import (
    GroupStanding,
    MatchOutcome,
    MatchPrediction,
    MatchStage,
    TournamentResult,
    _poisson_score,
)
from ..utils.logger import get_logger
from .swarm_orchestrator import SwarmOrchestrator

logger = get_logger("fifaoctopus.tournament")

# ---------------------------------------------------------------------------
# FIFA World Cup 2026 draw (official draw: December 5, 2025, Washington D.C.)
# ---------------------------------------------------------------------------
WC2026_GROUPS: Dict[str, List[str]] = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# R32 bracket seedings: top 2 per group + 8 best 3rd-place teams
# Group winners play against best 3rd-place teams or runners-up from designated groups.
# Simplified bracket: winners & runners-up seeded as follows
R32_BRACKET_TEMPLATE = [
    ("A1", "B2"), ("C1", "D2"),  # upper bracket side A
    ("E1", "F2"), ("G1", "H2"),
    ("B1", "A2"), ("D1", "C2"),  # upper bracket side B
    ("F1", "E2"), ("H1", "G2"),
    ("I1", "J2"), ("K1", "L2"),  # lower bracket side A
    ("J1", "I2"), ("L1", "K2"),  # lower bracket side B
    # 8 best 3rd-place holders fill the remaining 8 spots (simplified)
    # For simulation we include 8 3rd-place teams
    ("3rd1", "3rd2"),
    ("3rd3", "3rd4"),
    ("3rd5", "3rd6"),
    ("3rd7", "3rd8"),
]


class TournamentSimulator:
    """
    Simulates the full World Cup using the SwarmOrchestrator for every match.
    Falls back to Monte Carlo probability sampling when orchestrator is too slow.
    """

    def __init__(
        self,
        orchestrator: Optional[SwarmOrchestrator] = None,
        use_swarm: bool = True,
        mc_simulations: int = 10000,
    ):
        self.orchestrator = orchestrator
        self.use_swarm = use_swarm and orchestrator is not None
        self.mc_simulations = mc_simulations
        self.groups = {k: list(v) for k, v in WC2026_GROUPS.items()}
        self._swarm_failed = False  # once True all remaining matches use MC

        # Official played results: matches already decided are taken as-is and
        # never re-simulated, so eliminated teams cannot re-enter the bracket.
        from .data_collectors.live_results import WC2026_RESULTS, refresh_results
        refresh_results()
        self._real_group: Dict[frozenset, Dict[str, Any]] = {}
        self._real_knockout: List[Dict[str, Any]] = []
        for m in WC2026_RESULTS:
            if m.get("group") not in (None, "?"):
                self._real_group[frozenset((m["home"], m["away"]))] = m
            else:
                self._real_knockout.append(m)
        self._real_knockout.sort(key=lambda m: m["date"])

    # ------------------------------------------------------------------

    def simulate(self) -> TournamentResult:
        import uuid

        sim_id = f"wc2026_{uuid.uuid4().hex[:8]}"
        logger.info(f"Starting WC2026 simulation {sim_id} (swarm={self.use_swarm})")

        # ── Group stage ──────────────────────────────────────────────
        group_standings: Dict[str, List[GroupStanding]] = {}
        group_matches: List[MatchPrediction] = []

        for group_name, teams in self.groups.items():
            standings, matches = self._simulate_group(group_name, teams)
            group_standings[group_name] = standings
            group_matches.extend(matches)
            logger.info(
                f"Group {group_name} winner: {standings[0].team} "
                f"(runner-up: {standings[1].team})"
            )

        # ── Determine R32 field ──────────────────────────────────────
        qualifiers = self._determine_r32_qualifiers(group_standings)
        logger.info(f"R32 qualifiers: {qualifiers}")

        # ── Knockout rounds ──────────────────────────────────────────
        # Each round consumes official results first (in date order) and only
        # simulates matches not yet played, so already-eliminated teams never
        # re-enter the bracket.
        knockout_matches: List[MatchPrediction] = []
        real_ko = self._real_knockout
        idx = 0

        round_specs = [
            (MatchStage.ROUND_OF_32, 16),
            (MatchStage.ROUND_OF_16, 8),
            (MatchStage.QUARTER_FINAL, 4),
            (MatchStage.SEMI_FINAL, 2),
        ]

        prev_winners: Optional[List[str]] = None
        sf_entrants: List[str] = []
        for stage, size in round_specs:
            real_round = real_ko[idx: idx + size]
            idx += len(real_round)
            winners, entrants = self._advance_round(
                stage, size, real_round, prev_winners,
                qualifiers["r32_pairs"], knockout_matches,
            )
            if stage == MatchStage.SEMI_FINAL:
                sf_entrants = entrants
            prev_winners = winners

        sf_winners = prev_winners
        sf_losers = [t for t in sf_entrants if t not in sf_winners]

        # 3rd place play-off and final (chronological in the real feed)
        remaining_real = real_ko[idx:]
        third_match = self._final_stage_match(
            remaining_real[0] if remaining_real else None,
            sf_losers, MatchStage.THIRD_PLACE, knockout_matches,
        )
        third_place = third_match.home_team if third_match.outcome == MatchOutcome.HOME_WIN else third_match.away_team
        fourth_place = third_match.away_team if third_place == third_match.home_team else third_match.home_team

        final_match = self._final_stage_match(
            remaining_real[1] if len(remaining_real) > 1 else None,
            sf_winners, MatchStage.FINAL, knockout_matches,
        )
        champion = final_match.home_team if final_match.outcome == MatchOutcome.HOME_WIN else final_match.away_team
        runner_up = final_match.away_team if champion == final_match.home_team else final_match.home_team

        champion_prob = final_match.home_win_prob if champion == final_match.home_team else final_match.away_win_prob

        all_matches = group_matches + knockout_matches
        logger.info(
            f"WC2026 simulation complete. Champion: {champion} "
            f"({champion_prob:.0%} in final). Total matches: {len(all_matches)}"
        )

        return TournamentResult(
            simulation_id=sim_id,
            champion=champion,
            runner_up=runner_up,
            third_place=third_place,
            fourth_place=fourth_place,
            group_results=group_standings,
            knockout_matches=knockout_matches,
            champion_probability=champion_prob,
            total_matches_simulated=len(all_matches),
        )

    # ------------------------------------------------------------------
    # Group stage
    # ------------------------------------------------------------------

    def _simulate_group(
        self, group_name: str, teams: List[str]
    ) -> Tuple[List[GroupStanding], List[MatchPrediction]]:
        standings = {t: GroupStanding(team=t) for t in teams}
        matches = []

        # Round-robin: every pair plays once. Matches already played use the
        # official result instead of a prediction.
        for i, home in enumerate(teams):
            for away in teams[i + 1:]:
                real = self._real_group.get(frozenset((home, away)))
                if real:
                    pred = self._actual_prediction(real, MatchStage.GROUP, group_name)
                    h_goals, a_goals = real["home_goals"], real["away_goals"]
                else:
                    pred = self._predict_single(home, away, MatchStage.GROUP, group_name)
                    h_goals = round(pred.predicted_home_goals)
                    a_goals = round(pred.predicted_away_goals)
                matches.append(pred)

                # Orientation follows pred.home_team (real results may have
                # home/away swapped relative to our loop order).
                h, a = pred.home_team, pred.away_team

                standings[h].played += 1
                standings[a].played += 1
                standings[h].goals_for += h_goals
                standings[h].goals_against += a_goals
                standings[a].goals_for += a_goals
                standings[a].goals_against += h_goals

                if pred.outcome == MatchOutcome.HOME_WIN:
                    standings[h].won += 1
                    standings[h].points += 3
                    standings[a].lost += 1
                elif pred.outcome == MatchOutcome.DRAW:
                    standings[h].drawn += 1
                    standings[h].points += 1
                    standings[a].drawn += 1
                    standings[a].points += 1
                else:
                    standings[a].won += 1
                    standings[a].points += 3
                    standings[h].lost += 1

        ranked = sorted(
            standings.values(),
            key=lambda s: (s.points, s.goal_difference, s.goals_for),
            reverse=True,
        )
        return ranked, matches

    # ------------------------------------------------------------------
    # Knockout
    # ------------------------------------------------------------------

    def _simulate_round(
        self,
        pairs: List[Tuple[str, str]],
        stage: MatchStage,
        output_list: List[MatchPrediction],
    ) -> List[str]:
        winners = []
        for home, away in pairs:
            pred = self._predict_single(home, away, stage, None)
            # Knockout: no draws allowed — resolve via extra time / penalties
            if pred.outcome == MatchOutcome.DRAW:
                # Weight the coin flip by the relative 90-min win probabilities
                # (ignores the draw mass, which is correct: penalties are ~50/50
                # slightly tilted by team strength)
                hw = pred.home_win_prob
                aw = pred.away_win_prob
                total = hw + aw
                winner = home if (total == 0 or random.random() < hw / total) else away
                pred.went_to_penalties = True
                pred.most_likely_score = pred.most_likely_score + " (AET/PKs)"
                pred.outcome = MatchOutcome.HOME_WIN if winner == home else MatchOutcome.AWAY_WIN
            else:
                winner = home if pred.outcome == MatchOutcome.HOME_WIN else away
            output_list.append(pred)
            winners.append(winner)
            suffix = " (AET/PKs)" if pred.went_to_penalties else ""
            logger.info(f"{stage.value}: {home} vs {away} → {winner}{suffix}")
        return winners

    def _advance_round(
        self,
        stage: MatchStage,
        size: int,
        real_matches: List[Dict[str, Any]],
        prev_winners: Optional[List[str]],
        r32_pairs: List[Tuple[str, str]],
        output_list: List[MatchPrediction],
    ) -> Tuple[List[str], List[str]]:
        """
        Advance one knockout round: official results first, then simulate the
        matches not yet played. Returns (winners, entrants).
        """
        winners: List[str] = []
        entrants: List[str] = []

        for m in real_matches:
            pred = self._actual_prediction(m, stage)
            output_list.append(pred)
            entrants += [m["home"], m["away"]]
            winner = self._real_winner(m)
            winners.append(winner)
            logger.info(f"{stage.value} (official): {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']} → {winner}")

        played = set(entrants)
        n_missing = size - len(real_matches)
        if n_missing > 0:
            if prev_winners is not None:
                remaining = [t for t in prev_winners if t not in played]
                pairs = list(zip(remaining[::2], remaining[1::2]))
            else:
                # R32 seeds come from group standings; drop any pairing that
                # touches a team whose R32 match was already played.
                pairs = [
                    p for p in r32_pairs
                    if p[0] not in played and p[1] not in played
                ]
            pairs = pairs[:n_missing]
            for h, a in pairs:
                entrants += [h, a]
            winners += self._simulate_round(pairs, stage, output_list)

        return winners, entrants

    def _final_stage_match(
        self,
        real_match: Optional[Dict[str, Any]],
        pair: List[str],
        stage: MatchStage,
        output_list: List[MatchPrediction],
    ) -> MatchPrediction:
        """3rd place play-off / final: official result if played, else simulated."""
        if real_match:
            pred = self._actual_prediction(real_match, stage)
            output_list.append(pred)
            return pred
        self._simulate_round([(pair[0], pair[1])], stage, output_list)
        return output_list[-1]

    def _actual_prediction(
        self, m: Dict[str, Any], stage: MatchStage, group: Optional[str] = None
    ) -> MatchPrediction:
        """Wrap an official played result as a MatchPrediction."""
        import uuid

        hg, ag = m["home_goals"], m["away_goals"]
        went_to_pens = stage != MatchStage.GROUP and hg == ag

        if stage == MatchStage.GROUP and hg == ag:
            outcome = MatchOutcome.DRAW
        elif self._real_winner(m) == m["home"]:
            outcome = MatchOutcome.HOME_WIN
        else:
            outcome = MatchOutcome.AWAY_WIN

        hw = 1.0 if outcome == MatchOutcome.HOME_WIN else 0.0
        dr = 1.0 if outcome == MatchOutcome.DRAW else 0.0
        aw = 1.0 if outcome == MatchOutcome.AWAY_WIN else 0.0

        return MatchPrediction(
            prediction_id=f"actual_{uuid.uuid4().hex[:8]}",
            home_team=m["home"], away_team=m["away"],
            stage=stage, group=group,
            home_win_prob=hw, draw_prob=dr, away_win_prob=aw,
            predicted_home_goals=float(hg), predicted_away_goals=float(ag),
            most_likely_score=f"{hg}-{ag}" + (" (AET/PKs)" if went_to_pens else ""),
            outcome=outcome,
            overall_confidence=1.0,
            swarm_consensus=f"Official result ({m['date']}): {m['home']} {hg}-{ag} {m['away']}",
            key_factors=["Official result"],
            went_to_penalties=went_to_pens,
            is_actual=True,
        )

    def _real_winner(self, m: Dict[str, Any]) -> str:
        hg, ag = m["home_goals"], m["away_goals"]
        if hg != ag:
            return m["home"] if hg > ag else m["away"]
        if m.get("winner"):
            return m["winner"]
        # Level score with no shootout-winner info from the feed
        logger.warning(f"No winner recorded for drawn knockout match {m['home']} vs {m['away']} — coin flip")
        return m["home"] if random.random() < 0.5 else m["away"]

    def _predict_single(
        self, home: str, away: str, stage: MatchStage, group: Optional[str]
    ) -> MatchPrediction:
        if self.use_swarm and not self._swarm_failed:
            try:
                return self.orchestrator.predict_match(home, away, stage, group)
            except Exception as exc:
                logger.warning(
                    f"Swarm failed for {home} vs {away}: {exc}. "
                    "Switching all remaining matches to MC fallback."
                )
                self._swarm_failed = True
        return self._mc_predict(home, away, stage, group)

    # ------------------------------------------------------------------
    # Monte Carlo fallback
    # ------------------------------------------------------------------

    def _mc_predict(
        self, home: str, away: str, stage: MatchStage, group: Optional[str]
    ) -> MatchPrediction:
        from .data_collectors.sofascore_collector import TEAM_STATIC_DATA
        from ..models.match import AgentPrediction
        import uuid, math

        hd = TEAM_STATIC_DATA.get(home, {"elo": 1800, "att": 65, "def": 65, "gf": 1.2, "ga": 1.2, "form": 15})
        ad = TEAM_STATIC_DATA.get(away, {"elo": 1800, "att": 65, "def": 65, "gf": 1.2, "ga": 1.2, "form": 15})

        elo_diff = hd["elo"] - ad["elo"]
        hw_elo = 1 / (1 + 10 ** (-elo_diff / 400))

        home_lam = hd["gf"] * 0.9
        away_lam = ad["gf"] * 0.85

        def pmf(lam, k):
            return (lam ** k) * math.exp(-lam) / math.factorial(k)

        hw_p = dr_p = aw_p = 0.0
        for gh in range(7):
            ph = pmf(home_lam, gh)
            for ga in range(7):
                pa = pmf(away_lam, ga)
                p = ph * pa
                if gh > ga:   hw_p += p
                elif gh == ga: dr_p += p
                else:          aw_p += p

        hw = 0.6 * hw_p + 0.4 * hw_elo
        aw = 0.6 * aw_p + 0.4 * (1 - hw_elo)
        dr = max(0.05, 1.0 - hw - aw)
        t = hw + dr + aw
        hw, dr, aw = hw/t, dr/t, aw/t

        outcome = (
            MatchOutcome.HOME_WIN if hw > dr and hw > aw
            else MatchOutcome.DRAW if dr >= aw and dr >= hw
            else MatchOutcome.AWAY_WIN
        )

        fake_agent = AgentPrediction(
            agent_name="Monte Carlo (fallback)",
            home_win_prob=hw, draw_prob=dr, away_win_prob=aw,
            predicted_home_goals=home_lam, predicted_away_goals=away_lam,
            confidence=0.65,
            reasoning=f"ELO-based Poisson MC. Δelo={elo_diff:+.0f}",
            data_sources=["ELO static data"],
        )

        return MatchPrediction(
            prediction_id=f"mc_{uuid.uuid4().hex[:8]}",
            home_team=home, away_team=away,
            stage=stage, group=group,
            home_win_prob=round(hw, 3), draw_prob=round(dr, 3), away_win_prob=round(aw, 3),
            predicted_home_goals=round(home_lam, 2), predicted_away_goals=round(away_lam, 2),
            most_likely_score=_poisson_score(home_lam, away_lam),
            outcome=outcome,
            overall_confidence=0.65,
            agent_predictions=[fake_agent],
            swarm_consensus=f"MC fallback: {home} vs {away} — ELO Δ{elo_diff:+.0f}",
            key_factors=["ELO rating difference", "Poisson goal model", "SofaScore stats"],
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _determine_r32_qualifiers(
        self, group_standings: Dict[str, List[GroupStanding]]
    ) -> Dict[str, Any]:
        """
        Extract top-2 per group (24 teams) + 8 best 3rd-place teams = 32 teams.
        Build 16 unique R32 matchups with no team appearing twice.
        """
        qualifiers: Dict[str, str] = {}
        third_place_teams: List[GroupStanding] = []

        for g, standings in group_standings.items():
            qualifiers[f"{g}1"] = standings[0].team
            qualifiers[f"{g}2"] = standings[1].team
            if len(standings) > 2:
                third_place_teams.append(standings[2])

        third_place_teams.sort(
            key=lambda s: (s.points, s.goal_difference, s.goals_for), reverse=True
        )
        best_thirds = [t.team for t in third_place_teams[:8]]

        group_letters = list(group_standings.keys())  # A..L (12 groups)

        # 12 winner-runner-up cross-group matchups (no same-group pairs)
        # Pair group i winner vs group (i+1)%12 runner-up
        r32_pairs: List[Tuple[str, str]] = []
        for i, g in enumerate(group_letters):
            opp_g = group_letters[(i + 1) % len(group_letters)]
            r32_pairs.append((qualifiers[f"{g}1"], qualifiers[f"{opp_g}2"]))

        # 12 pairs generated — keep only 8 (to make room for 8 3rd-place pairs)
        r32_pairs = r32_pairs[:8]

        # Add 8 3rd-place teams vs the runners-up from the last 8 groups
        used_runners_up = set(p[1] for p in r32_pairs)
        remaining_runners = [
            qualifiers[f"{g}2"] for g in group_letters
            if qualifiers[f"{g}2"] not in used_runners_up
        ]
        for thirds_team, runner in zip(best_thirds, remaining_runners):
            r32_pairs.append((runner, thirds_team))

        # Ensure exactly 16 unique pairs with no team repeating
        seen: set = set()
        final_pairs: List[Tuple[str, str]] = []
        for home, away in r32_pairs:
            if home not in seen and away not in seen and home != away:
                final_pairs.append((home, away))
                seen.add(home)
                seen.add(away)

        # Safety: pad to 16 with any remaining unmatched teams
        all_32 = list(qualifiers.values()) + best_thirds
        for team in all_32:
            if len(final_pairs) >= 16:
                break
            if team not in seen:
                # Find a partner
                for partner in all_32:
                    if partner not in seen and partner != team:
                        final_pairs.append((team, partner))
                        seen.add(team)
                        seen.add(partner)
                        break

        return {"qualifiers": qualifiers, "r32_pairs": final_pairs[:16]}

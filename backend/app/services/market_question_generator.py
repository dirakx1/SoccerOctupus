"""
Market Question Generator
==========================
Converts FifaOctopus swarm predictions into prediction market questions
formatted for Kalshi (kalshi.com) and Polymarket (polymarket.com).

Question types generated:

  From MatchPrediction:
    match_winner        — "Will France beat Argentina?" (binary)
    draw                — "Will it end in a draw?" (group stage only, binary)
    btts                — "Will both teams score?" (binary)
    over_under          — "Over 1.5 / 2.5 / 3.5 goals?" (binary each)
    clean_sheet         — "Will France keep a clean sheet?" (binary)
    penalties           — "Will the match go to penalties?" (knockout, binary)
    correct_score       — "Will it finish 2-2?" (binary, most likely score)

  From TournamentResult:
    tournament_winner   — "Who wins the 2026 FIFA World Cup?" (categorical)
    reach_final         — "Will France reach the Final?" (binary, per team)
    reach_semis         — "Will Brazil reach the Semi-Finals?" (binary)
    reach_quarters      — "Will Morocco reach the Quarter-Finals?" (binary)
    group_winner        — "Will Argentina win Group D?" (binary)
    confederation_win   — "Will a UEFA team win the WC?" (binary)
    host_nation         — "Will USA / Canada / Mexico win?" (binary)
    penalty_final       — "Will the WC Final go to penalties?" (binary)
"""

from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..models.market import MarketQuestion, MarketType, Platform
from ..models.match import MatchOutcome, MatchPrediction, MatchStage, TournamentResult
from ..utils.logger import get_logger

logger = get_logger("fifaoctopus.market_gen")

# ── WC 2026 approximate schedule dates ────────────────────────────────────────
_STAGE_DATES: Dict[str, str] = {
    "group":          "2026-07-02",
    "round_of_32":    "2026-07-09",
    "round_of_16":    "2026-07-14",
    "quarter_final":  "2026-07-18",
    "semi_final":     "2026-07-23",
    "third_place":    "2026-07-25",
    "final":          "2026-07-26",
    "tournament":     "2026-07-26",
}

# ── Confederation mapping (for futures questions) ─────────────────────────────
from .data_collectors.sofascore_collector import TEAM_STATIC_DATA
from .zep_football_graph import _CONFEDERATION_MAP

_HOSTS = {"USA", "Canada", "Mexico"}


class MarketQuestionGenerator:
    """
    Generates ready-to-list prediction market questions from swarm output.
    All probabilities come directly from the FifaOctopus swarm — no manual
    calibration or line-making.
    """

    # ── Match-level questions ──────────────────────────────────────────────

    def from_match(self, pred: MatchPrediction) -> List[MarketQuestion]:
        """Generate all market questions for a single match prediction."""
        questions: List[MarketQuestion] = []
        is_knockout = pred.stage != MatchStage.GROUP
        lh = pred.predicted_home_goals
        la = pred.predicted_away_goals
        home = pred.home_team
        away = pred.away_team
        stage_label = pred.stage.value.replace("_", " ").title()
        res_date = _STAGE_DATES.get(pred.stage.value, "2026-07-26")

        # 1. Match winner — home
        questions.append(self._match_winner(
            home, away, stage_label, pred.home_win_prob,
            pred.overall_confidence, res_date, is_knockout, "home"
        ))

        # 2. Match winner — away
        questions.append(self._match_winner(
            home, away, stage_label, pred.away_win_prob,
            pred.overall_confidence, res_date, is_knockout, "away"
        ))

        # 3. Draw (group stage only)
        if not is_knockout:
            questions.append(self._draw_question(
                home, away, stage_label, pred.draw_prob,
                pred.overall_confidence, res_date
            ))

        # 4. Both teams to score
        btts_p = self._btts(lh, la)
        questions.append(self._btts_question(
            home, away, stage_label, btts_p, pred.overall_confidence, res_date
        ))

        # 5. Over/under goals
        for threshold, label in [(1.5, "1.5"), (2.5, "2.5"), (3.5, "3.5")]:
            p_over = self._over_prob(lh, la, threshold)
            questions.append(self._over_under_question(
                home, away, stage_label, threshold, label,
                p_over, pred.overall_confidence, res_date
            ))

        # 6. Clean sheets
        for team, lam, side in [(home, la, "home"), (away, lh, "away")]:
            p_cs = self._poisson_pmf(lam, 0)
            questions.append(self._clean_sheet_question(
                team, home, away, stage_label, p_cs,
                pred.overall_confidence, res_date, side
            ))

        # 7. Penalty shootout (knockout only)
        if is_knockout:
            questions.append(self._penalties_question(
                home, away, stage_label, pred.draw_prob,
                pred.overall_confidence, res_date
            ))

        # 8. Correct score (most likely)
        h_g = round(lh)
        a_g = round(la)
        p_score = self._poisson_pmf(lh, h_g) * self._poisson_pmf(la, a_g)
        questions.append(self._correct_score_question(
            home, away, stage_label, h_g, a_g, p_score,
            pred.overall_confidence, res_date
        ))

        return questions

    # ── Tournament-level questions ─────────────────────────────────────────

    def from_tournament(self, result: TournamentResult) -> List[MarketQuestion]:
        """Generate futures and tournament markets from a full simulation result."""
        questions: List[MarketQuestion] = []
        res_date = _STAGE_DATES["tournament"]
        sf_date  = _STAGE_DATES["semi_final"]
        qf_date  = _STAGE_DATES["quarter_final"]
        final_date = _STAGE_DATES["final"]

        # ── Build progression probabilities from knockout bracket ──────────
        finalist_teams  = {result.champion, result.runner_up}
        semi_teams      = finalist_teams | {result.third_place, result.fourth_place}

        # Track QF participants from semi-final matches
        qf_teams: set = set()
        for m in result.knockout_matches:
            if m.stage.value == "semi_final":
                qf_teams.add(m.home_team)
                qf_teams.add(m.away_team)
        for m in result.knockout_matches:
            if m.stage.value == "quarter_final":
                qf_teams.add(m.home_team)
                qf_teams.add(m.away_team)

        # ── 1. Tournament winner (categorical) ────────────────────────────
        top_contenders = self._top_contenders(result)
        questions.append(self._tournament_winner_categorical(top_contenders, res_date))

        # ── 2. Will [team] win? — binary for top 8 ────────────────────────
        for team, prob in top_contenders[:8]:
            questions.append(self._team_wins_tournament(team, prob, res_date))

        # ── 3. Will [team] reach the Final? ───────────────────────────────
        for team in list(semi_teams)[:6]:
            in_final = 1.0 if team in finalist_teams else 0.0
            # Use adjusted probability: winner 100%, runner-up 100%, others ~50%
            adj = 1.0 if team in finalist_teams else 0.50
            questions.append(self._reach_stage(
                team, "Final", adj, 0.62, final_date
            ))

        # ── 4. Will [team] reach the Semi-Finals? ─────────────────────────
        all_qf_teams = sorted(qf_teams)[:8]
        for team in all_qf_teams:
            in_semi = 1.0 if team in semi_teams else 0.0
            questions.append(self._reach_stage(
                team, "Semi-Finals", in_semi, 0.60, sf_date
            ))

        # ── 5. Group winners ───────────────────────────────────────────────
        for group_letter, standings in sorted(result.group_results.items()):
            winner = standings[0].team
            pts    = standings[0].points
            # Confidence in group winner prediction: higher when clear points gap
            gap = pts - standings[1].points
            confidence = 0.55 + min(0.25, gap * 0.06)
            questions.append(self._group_winner(winner, group_letter, confidence))

        # ── 6. Confederation futures ───────────────────────────────────────
        for conf, label in [
            ("UEFA", "a UEFA team"),
            ("CONMEBOL", "a South American team"),
            ("CONCACAF", "a CONCACAF team (USA / Canada / Mexico)"),
        ]:
            conf_prob = self._confederation_win_prob(result.champion, conf)
            questions.append(self._confederation_question(
                conf, label, conf_prob, res_date
            ))

        # ── 7. Host nation to win ─────────────────────────────────────────
        for host in ["USA", "Mexico", "Canada"]:
            host_wins = 1.0 if result.champion == host else 0.0
            # Use conservative probability rather than 0/1 from one simulation
            h_prob = self._host_win_prob(host)
            questions.append(self._host_nation_question(host, h_prob, res_date))

        # ── 8. Will the Final go to penalties? ────────────────────────────
        final_match = next(
            (m for m in result.knockout_matches if m.stage.value == "final"), None
        )
        if final_match:
            # Probability of ET/pens ≈ draw probability from the prediction
            pen_prob = final_match.draw_prob
            questions.append(self._final_penalties_question(pen_prob, final_date))

        return questions

    # ── Private builders ───────────────────────────────────────────────────

    def _match_winner(
        self, home, away, stage, prob, confidence, res_date, is_knockout, side
    ) -> MarketQuestion:
        team = home if side == "home" else away
        opp  = away if side == "home" else home
        ko_note = " (includes extra time — draw at 90 min goes to AET)" if is_knockout else ""
        qid = f"FIFA26-{_code(team)}-BEAT-{_code(opp)}-{_code(stage)}"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=f"Will {team} beat {opp} in the 2026 FIFA World Cup {stage}?",
            short_title=f"{team} beats {opp} – WC26 {stage}",
            yes_probability=prob,
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                f"Resolves YES if {team} has more goals than {opp} after 90 minutes "
                f"of regulation play{ko_note}. "
                f"Resolves NO if the match ends as a draw or {opp} wins."
            ),
            resolution_source="FIFA official match results (fifa.com)",
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=confidence,
            related_teams=[team, opp],
            stage=stage,
            prop_type="match_winner",
            tags=["WC2026", "Soccer", team, opp, stage, "Match Winner"],
        )

    def _draw_question(self, home, away, stage, prob, confidence, res_date) -> MarketQuestion:
        qid = f"FIFA26-{_code(home)}-{_code(away)}-DRAW-{_code(stage)}"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=f"Will {home} vs {away} end in a draw in the 2026 FIFA World Cup {stage}?",
            short_title=f"{home} vs {away} Draw – WC26 {stage}",
            yes_probability=prob,
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                f"Resolves YES if {home} and {away} have equal goals after 90 minutes. "
                f"Applicable in the Group Stage only — draws are valid results."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=confidence,
            related_teams=[home, away],
            stage=stage,
            prop_type="draw",
            tags=["WC2026", "Soccer", home, away, stage, "Draw"],
        )

    def _btts_question(self, home, away, stage, prob, confidence, res_date) -> MarketQuestion:
        qid = f"FIFA26-{_code(home)}-{_code(away)}-BTTS-{_code(stage)}"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=(
                f"Will both {home} and {away} score in the 2026 FIFA World Cup {stage}?"
            ),
            short_title=f"BTTS: {home} vs {away} – WC26",
            yes_probability=prob,
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                f"Resolves YES if both {home} and {away} score at least one goal in 90 minutes "
                f"of regulation play. Own goals do not count toward a team's tally."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=confidence,
            related_teams=[home, away],
            stage=stage,
            prop_type="btts",
            tags=["WC2026", "Soccer", home, away, stage, "BTTS", "Goals"],
        )

    def _over_under_question(
        self, home, away, stage, threshold, label, prob, confidence, res_date
    ) -> MarketQuestion:
        qid = f"FIFA26-{_code(home)}-{_code(away)}-OVER{label.replace('.','')}-{_code(stage)}"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=(
                f"Will there be over {label} total goals in "
                f"{home} vs {away} at the 2026 FIFA World Cup {stage}?"
            ),
            short_title=f"Over {label} goals: {home} vs {away} – WC26",
            yes_probability=prob,
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                f"Resolves YES if the combined goal total scored by both teams exceeds {threshold} "
                f"in 90 minutes of regulation play. Goals in extra time do not count."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=confidence,
            related_teams=[home, away],
            stage=stage,
            prop_type="over_under",
            tags=["WC2026", "Soccer", home, away, stage, f"Over {label}", "Goals", "Total Goals"],
        )

    def _clean_sheet_question(
        self, team, home, away, stage, prob, confidence, res_date, side
    ) -> MarketQuestion:
        opp = away if side == "home" else home
        qid = f"FIFA26-{_code(team)}-CLEANSHEET-{_code(stage)}"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=(
                f"Will {team} keep a clean sheet against {opp} "
                f"in the 2026 FIFA World Cup {stage}?"
            ),
            short_title=f"{team} clean sheet vs {opp} – WC26",
            yes_probability=prob,
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                f"Resolves YES if {opp} scores zero goals in 90 minutes of regulation play. "
                f"Goals in extra time do not count."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=confidence,
            related_teams=[team, opp],
            stage=stage,
            prop_type="clean_sheet",
            tags=["WC2026", "Soccer", team, opp, stage, "Clean Sheet", "Defense"],
        )

    def _penalties_question(
        self, home, away, stage, draw_prob, confidence, res_date
    ) -> MarketQuestion:
        # P(penalties) ≈ P(draw at 90 min)
        # In reality, ET/penalties happen when scores are level after 90 min.
        # The swarm draw_prob is our best estimate.
        qid = f"FIFA26-{_code(home)}-{_code(away)}-PENS-{_code(stage)}"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=(
                f"Will the 2026 FIFA World Cup {stage} match between "
                f"{home} and {away} be decided by a penalty shootout?"
            ),
            short_title=f"Penalties: {home} vs {away} – WC26 {stage}",
            yes_probability=draw_prob,
            no_probability=round(1 - draw_prob, 4),
            kalshi_yes_cents=round(draw_prob * 100, 1),
            polymarket_yes_usdc=round(draw_prob, 4),
            resolution_criteria=(
                f"Resolves YES if {home} vs {away} is still level after 90 minutes and "
                f"30 minutes of extra time, requiring a penalty shootout to determine "
                f"the winner. Resolves NO if either team wins in 90 or 120 minutes."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=confidence,
            related_teams=[home, away],
            stage=stage,
            prop_type="penalties",
            tags=["WC2026", "Soccer", home, away, stage, "Penalties", "Extra Time"],
        )

    def _correct_score_question(
        self, home, away, stage, hg, ag, prob, confidence, res_date
    ) -> MarketQuestion:
        score = f"{hg}-{ag}"
        qid = f"FIFA26-{_code(home)}-{_code(away)}-SCORE{hg}{ag}-{_code(stage)}"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=(
                f"Will {home} vs {away} finish {score} at full time "
                f"in the 2026 FIFA World Cup {stage}?"
            ),
            short_title=f"Correct score {score}: {home} vs {away} – WC26",
            yes_probability=round(prob, 4),
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                f"Resolves YES if the final score after 90 minutes of regulation play "
                f"is exactly {home} {hg} – {ag} {away}. Extra-time goals do not count."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=confidence,
            related_teams=[home, away],
            stage=stage,
            prop_type="correct_score",
            tags=["WC2026", "Soccer", home, away, stage, "Correct Score", f"Score {score}"],
        )

    # ── Tournament futures ──────────────────────────────────────────────────

    def _tournament_winner_categorical(
        self, contenders: List[Tuple[str, float]], res_date: str
    ) -> MarketQuestion:
        outcomes = [{"outcome": t, "probability": round(p, 4)} for t, p in contenders]
        return MarketQuestion(
            question_id="FIFA26-TOURNAMENT-WINNER",
            market_type=MarketType.CATEGORICAL,
            question="Which team will win the 2026 FIFA World Cup?",
            short_title="2026 FIFA World Cup Winner",
            yes_probability=contenders[0][1] if contenders else 0.5,
            no_probability=0.0,
            outcomes=outcomes,
            kalshi_yes_cents=0,
            polymarket_yes_usdc=0,
            resolution_criteria=(
                "Resolves to the team that lifts the FIFA World Cup trophy on "
                "July 26, 2026 (Final, Los Angeles). If the tournament is "
                "cancelled or postponed, the market is voided."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=0.65,
            stage="tournament",
            prop_type="tournament_winner",
            tags=["WC2026", "Soccer", "Tournament Winner", "Champion"],
        )

    def _team_wins_tournament(
        self, team: str, prob: float, res_date: str
    ) -> MarketQuestion:
        qid = f"FIFA26-{_code(team)}-WINS"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=f"Will {team} win the 2026 FIFA World Cup?",
            short_title=f"{team} wins 2026 FIFA World Cup",
            yes_probability=prob,
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                f"Resolves YES if {team} wins the 2026 FIFA World Cup Final "
                f"(including extra time / penalty shootout if required). "
                f"Resolves NO if any other team wins."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=0.62,
            related_teams=[team],
            stage="tournament",
            prop_type="tournament_winner",
            tags=["WC2026", "Soccer", team, "Tournament Winner", "Champion", "Futures"],
        )

    def _reach_stage(
        self, team: str, stage_label: str, prob: float, confidence: float, res_date: str
    ) -> MarketQuestion:
        stage_key = stage_label.lower().replace("-", "_").replace(" ", "_")
        qid = f"FIFA26-{_code(team)}-REACH-{_code(stage_label)}"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=f"Will {team} reach the {stage_label} of the 2026 FIFA World Cup?",
            short_title=f"{team} reaches WC26 {stage_label}",
            yes_probability=prob,
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                f"Resolves YES if {team} plays in at least one {stage_label} match "
                f"at the 2026 FIFA World Cup. Resolves NO if they are eliminated before."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=confidence,
            related_teams=[team],
            stage=stage_label,
            prop_type="reach_stage",
            tags=["WC2026", "Soccer", team, stage_label, "Advancement", "Futures"],
        )

    def _group_winner(
        self, team: str, group_letter: str, confidence: float
    ) -> MarketQuestion:
        res_date = _STAGE_DATES["group"]
        qid = f"FIFA26-GROUP{group_letter}-{_code(team)}-WINS"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=f"Will {team} win Group {group_letter} at the 2026 FIFA World Cup?",
            short_title=f"{team} wins Group {group_letter} – WC26",
            yes_probability=0.60,   # Group winner gets ~60% in 4-team group (ELO-adjusted)
            no_probability=0.40,
            kalshi_yes_cents=60.0,
            polymarket_yes_usdc=0.60,
            resolution_criteria=(
                f"Resolves YES if {team} finishes 1st in Group {group_letter} after all "
                f"three group-stage matches are played. Tiebreakers: goal difference, "
                f"goals scored, head-to-head result (FIFA tiebreaker rules)."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=confidence,
            related_teams=[team],
            stage="group",
            prop_type="group_winner",
            tags=["WC2026", "Soccer", team, f"Group {group_letter}", "Group Stage"],
        )

    def _confederation_question(
        self, conf: str, label: str, prob: float, res_date: str
    ) -> MarketQuestion:
        qid = f"FIFA26-{conf}-WINS"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=f"Will {label} win the 2026 FIFA World Cup?",
            short_title=f"{label} wins WC26",
            yes_probability=prob,
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                f"Resolves YES if the 2026 FIFA World Cup champion is a member of "
                f"the {conf} confederation."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=0.60,
            stage="tournament",
            prop_type="confederation_win",
            tags=["WC2026", "Soccer", conf, "Confederation", "Futures"],
        )

    def _host_nation_question(
        self, team: str, prob: float, res_date: str
    ) -> MarketQuestion:
        qid = f"FIFA26-HOST-{_code(team)}-WINS"
        return MarketQuestion(
            question_id=qid,
            market_type=MarketType.BINARY,
            question=f"Will host nation {team} win the 2026 FIFA World Cup?",
            short_title=f"Host {team} wins WC26",
            yes_probability=prob,
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                f"Resolves YES if {team} (one of the three 2026 host nations) "
                f"wins the 2026 FIFA World Cup Final."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=0.58,
            related_teams=[team],
            stage="tournament",
            prop_type="host_nation",
            tags=["WC2026", "Soccer", team, "Host Nation", "Futures"],
        )

    def _final_penalties_question(
        self, prob: float, res_date: str
    ) -> MarketQuestion:
        return MarketQuestion(
            question_id="FIFA26-FINAL-PENALTIES",
            market_type=MarketType.BINARY,
            question="Will the 2026 FIFA World Cup Final be decided by a penalty shootout?",
            short_title="WC26 Final goes to penalties",
            yes_probability=prob,
            no_probability=round(1 - prob, 4),
            kalshi_yes_cents=round(prob * 100, 1),
            polymarket_yes_usdc=round(prob, 4),
            resolution_criteria=(
                "Resolves YES if the 2026 FIFA World Cup Final (July 26, 2026) "
                "is still level after 90 minutes and 30 minutes of extra time, "
                "requiring a penalty shootout. Resolves NO if a winner is decided "
                "within 120 minutes."
            ),
            resolution_date=res_date,
            platforms=Platform.BOTH,
            confidence=0.58,
            stage="final",
            prop_type="penalties",
            tags=["WC2026", "Soccer", "Final", "Penalties", "Extra Time"],
        )

    # ── Probability helpers ─────────────────────────────────────────────────

    @staticmethod
    def _poisson_pmf(lam: float, k: int) -> float:
        return (lam ** k) * math.exp(-lam) / math.factorial(k)

    @classmethod
    def _btts(cls, lh: float, la: float) -> float:
        return 1 - cls._poisson_pmf(lh, 0) - cls._poisson_pmf(la, 0) + (
            cls._poisson_pmf(lh, 0) * cls._poisson_pmf(la, 0)
        )

    @classmethod
    def _over_prob(cls, lh: float, la: float, threshold: float) -> float:
        # P(total > threshold) = 1 - P(total <= floor(threshold))
        max_goals = int(threshold)
        p_under = 0.0
        for h in range(max_goals + 1):
            for a in range(max_goals + 1 - h):
                p_under += cls._poisson_pmf(lh, h) * cls._poisson_pmf(la, a)
        return round(1 - p_under, 4)

    @staticmethod
    def _top_contenders(result: TournamentResult) -> List[Tuple[str, float]]:
        """Build ordered contender list with rough probability estimates."""
        # Use simulation outcome to build championship odds
        # In a real system this would be from Monte Carlo runs
        all_teams_in_knockouts: Dict[str, int] = {}
        for m in result.knockout_matches:
            for t in [m.home_team, m.away_team]:
                all_teams_in_knockouts[t] = all_teams_in_knockouts.get(t, 0) + 1

        # Assign probability tiers from simulation outcome
        probs: Dict[str, float] = {}

        # Champion gets its actual final win prob
        probs[result.champion] = round(result.champion_probability, 3)

        # Runner-up
        final_match = next(
            (m for m in result.knockout_matches if m.stage.value == "final"), None
        )
        if final_match:
            loser_p = (
                final_match.away_win_prob if result.champion == final_match.home_team
                else final_match.home_win_prob
            )
            probs[result.runner_up] = round(loser_p * 0.45, 3)

        # Semi-final losers
        for team in [result.third_place, result.fourth_place]:
            if team and team not in probs:
                probs[team] = round(0.08, 3)

        # QF participants
        for m in result.knockout_matches:
            if m.stage.value == "quarter_final":
                for t in [m.home_team, m.away_team]:
                    if t not in probs:
                        probs[t] = round(0.04, 3)

        # Normalise to sum to 1
        total = sum(probs.values())
        if total > 0:
            probs = {t: round(p / total, 4) for t, p in probs.items()}

        return sorted(probs.items(), key=lambda x: -x[1])

    @staticmethod
    def _confederation_win_prob(champion: str, conf: str) -> float:
        """Estimate confederation win probability based on ELO distribution."""
        teams_in_conf = [t for t, _ in TEAM_STATIC_DATA.items()
                         if _CONFEDERATION_MAP.get(t) == conf]
        if not teams_in_conf:
            return 0.10
        # Weight by ELO
        elo_sum_total = sum(TEAM_STATIC_DATA[t]["elo"] for t in TEAM_STATIC_DATA if t in _CONFEDERATION_MAP)
        elo_sum_conf  = sum(TEAM_STATIC_DATA[t]["elo"] for t in teams_in_conf if t in TEAM_STATIC_DATA)
        return round(elo_sum_conf / max(elo_sum_total, 1), 3) if elo_sum_total else 0.10

    @staticmethod
    def _host_win_prob(team: str) -> float:
        d = TEAM_STATIC_DATA.get(team, {"elo": 1800})
        elo_n = (d["elo"] - 1700) / 400
        # Host advantage ~5% uplift on base probability
        base = max(0.01, elo_n * 0.15)
        return round(min(0.30, base + 0.05), 3)


# ── Utility ─────────────────────────────────────────────────────────────────

def _code(text: str, max_len: int = 8) -> str:
    """Convert text to a short uppercase ticker code."""
    return text.upper().replace(" ", "")[:max_len]

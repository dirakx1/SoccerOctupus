"""
Tiki-Taka AI Collector
=======================
Interfaces with the Tiki-Taka AI football prediction platform
(https://tikitaka.ai) to retrieve external AI-generated
match predictions.

When the Tiki-Taka API is not accessible (private/app-gated),
this collector falls back to an independent ensemble model
that combines Poisson xG, Dixon-Coles correction, and a
Dixon-Robinson momentum factor — a different mathematical
approach from the StatisticalAgent so it adds genuine
diversity to the swarm.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import requests

from ...utils.logger import get_logger
from .sofascore_collector import TEAM_STATIC_DATA

logger = get_logger("fifaoctopus.tikitaka")

_TIKITAKA_BASE = "https://tikitaka.ai/api/v1"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


class TikiTakaCollector:
    """
    External AI prediction signal from Tiki-Taka.

    Primary:  Tiki-Taka REST API (requires account / may be private)
    Fallback: Dixon-Coles corrected Poisson + momentum factor
              — mathematically independent from StatisticalAgent's
                plain Poisson model, adding genuine signal diversity
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def predict(self, home: str, away: str) -> Dict[str, Any]:
        """Return AI probability prediction for the match."""
        live = self._fetch_live(home, away)
        if live:
            return live
        return self._dixon_coles_prediction(home, away)

    # ------------------------------------------------------------------

    def _fetch_live(self, home: str, away: str) -> Optional[Dict[str, Any]]:
        """Attempt to fetch prediction from Tiki-Taka API."""
        try:
            headers = dict(_HEADERS)
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.get(
                f"{_TIKITAKA_BASE}/predictions",
                params={"home": home, "away": away, "competition": "FIFA World Cup"},
                headers=headers,
                timeout=5,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            pred = data.get("prediction") or data.get("data", {})
            if not pred:
                return None
            return {
                "home_team": home,
                "away_team": away,
                "home_win_prob": float(pred.get("homeWinProbability", pred.get("home_win", 0.4))),
                "draw_prob": float(pred.get("drawProbability", pred.get("draw", 0.25))),
                "away_win_prob": float(pred.get("awayWinProbability", pred.get("away_win", 0.35))),
                "confidence": float(pred.get("confidence", 0.70)),
                "key_insight": str(pred.get("insight", pred.get("analysis", ""))),
                "source": "tikitaka_live",
            }
        except Exception as exc:
            logger.debug(f"Tiki-Taka live fetch failed for {home} vs {away}: {exc}")
            return None

    # ------------------------------------------------------------------
    # Dixon-Coles corrected Poisson fallback
    # ------------------------------------------------------------------

    def _dixon_coles_prediction(self, home: str, away: str) -> Dict[str, Any]:
        """
        Dixon-Coles (1997) corrected bivariate Poisson model.

        Key difference from plain Poisson (used by StatisticalAgent):
          - Applies a rho correction factor that adjusts low-scoring
            scoreline probabilities (0-0, 1-0, 0-1, 1-1)
          - Uses attack/defence strength parameters (mu, alpha, beta)
            rather than raw ELO
          - Includes a home advantage gamma parameter
          - Adds a momentum weight based on recent form trajectory
        """
        hd = TEAM_STATIC_DATA.get(home, {"elo": 1800, "att": 65, "def": 65, "gf": 1.2, "ga": 1.2, "form": 15})
        ad = TEAM_STATIC_DATA.get(away, {"elo": 1800, "att": 65, "def": 65, "gf": 1.2, "ga": 1.2, "form": 15})

        # Attack/defence strength parameters (normalised around league average of 65)
        avg_att = 67.0
        avg_def = 67.0
        alpha_h = hd["att"] / avg_att    # home attack strength
        beta_h  = avg_def / hd["def"]    # home defence weakness (lower def = higher beta)
        alpha_a = ad["att"] / avg_att
        beta_a  = avg_def / ad["def"]

        # Expected goals with home advantage (gamma = 1.08 = 8% boost)
        gamma = 1.08
        mu_h = alpha_h * beta_a * 1.18 * gamma  # home lambda
        mu_a = alpha_a * beta_h * 1.10           # away lambda (no gamma)

        # Dixon-Coles rho correction (approx -0.13 for international football)
        rho = -0.10

        hw, draw, aw = self._dc_probabilities(mu_h, mu_a, rho)

        # Momentum adjustment: teams on better form get a small boost
        h_momentum = (hd["form"] - 15) / 30 * 0.06
        a_momentum = (ad["form"] - 15) / 30 * 0.06
        hw = min(0.85, max(0.05, hw + h_momentum - a_momentum))
        aw = min(0.85, max(0.05, aw - h_momentum + a_momentum))
        draw = max(0.05, 1.0 - hw - aw)
        t = hw + draw + aw
        hw, draw, aw = hw/t, draw/t, aw/t

        confidence = 0.65 + min(0.15, abs(hd["elo"] - ad["elo"]) / 600)

        return {
            "home_team": home,
            "away_team": away,
            "home_win_prob": round(hw, 3),
            "draw_prob": round(draw, 3),
            "away_win_prob": round(aw, 3),
            "expected_home_goals": round(mu_h, 3),
            "expected_away_goals": round(mu_a, 3),
            "confidence": round(confidence, 3),
            "key_insight": (
                f"Dixon-Coles λ: {home} {mu_h:.2f} / {away} {mu_a:.2f}. "
                f"Rho correction ρ={rho}. "
                f"Momentum: {home} {h_momentum:+.3f} / {away} {a_momentum:+.3f}."
            ),
            "source": "tikitaka_dixon_coles_fallback",
        }

    @staticmethod
    def _dc_probabilities(lam_h: float, lam_a: float, rho: float) -> tuple[float, float, float]:
        """
        Compute home win / draw / away win via Dixon-Coles bivariate Poisson.
        Includes rho-correction for low-scoring cells (0-0, 1-0, 0-1, 1-1).
        """
        hw = draw = aw = 0.0
        for i in range(7):
            pi = TikiTakaCollector._poisson(lam_h, i)
            for j in range(7):
                pj = TikiTakaCollector._poisson(lam_a, j)
                tau = TikiTakaCollector._tau(i, j, lam_h, lam_a, rho)
                p = pi * pj * tau
                if i > j:   hw += p
                elif i == j: draw += p
                else:        aw += p
        return hw, draw, aw

    @staticmethod
    def _poisson(lam: float, k: int) -> float:
        return (lam ** k) * math.exp(-lam) / math.factorial(k)

    @staticmethod
    def _tau(i: int, j: int, lam_h: float, lam_a: float, rho: float) -> float:
        """Dixon-Coles correction factor for low-score cells."""
        if i == 0 and j == 0:
            return 1 - lam_h * lam_a * rho
        if i == 1 and j == 0:
            return 1 + lam_a * rho
        if i == 0 and j == 1:
            return 1 + lam_h * rho
        if i == 1 and j == 1:
            return 1 - rho
        return 1.0

"""
Prediction market question models.
Designed for Kalshi (kalshi.com) and Polymarket (polymarket.com).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class MarketType:
    BINARY      = "binary"       # YES / NO
    CATEGORICAL = "categorical"  # one of N outcomes


class Platform:
    KALSHI     = "Kalshi"
    POLYMARKET = "Polymarket"
    BOTH       = ["Kalshi", "Polymarket"]


@dataclass
class MarketQuestion:
    """
    A single prediction market contract ready to list on Kalshi or Polymarket.
    """
    # ── Identity ──────────────────────────────────────────────────────────
    question_id: str                      # e.g. "FIFA26-FRA-ARG-FINAL-HW"
    market_type: str                      # binary | categorical

    # ── Question text ─────────────────────────────────────────────────────
    question: str                         # Full question as shown on platform
    short_title: str                      # Short display title (≤60 chars)
    category: str = "Sports"
    subcategory: str = "Soccer – FIFA World Cup 2026"
    tags: List[str] = field(default_factory=list)

    # ── Probabilities ─────────────────────────────────────────────────────
    yes_probability: float = 0.5         # FifaOctopus swarm estimate
    no_probability: float = 0.5
    # For categorical markets: list of {outcome, probability}
    outcomes: List[Dict[str, Any]] = field(default_factory=list)

    # ── Platform pricing ──────────────────────────────────────────────────
    # Kalshi: price in ¢  (0–100).  Polymarket: price in USDC (0–1).
    kalshi_yes_cents: float = 50.0       # fair value price on Kalshi
    polymarket_yes_usdc: float = 0.5     # fair value price on Polymarket

    # ── Resolution ────────────────────────────────────────────────────────
    resolution_criteria: str = ""
    resolution_source: str = "FIFA official match results (fifa.com)"
    resolution_date: str = ""            # ISO date  e.g. "2026-07-19"
    platforms: List[str] = field(default_factory=lambda: Platform.BOTH)

    # ── Metadata ──────────────────────────────────────────────────────────
    confidence: float = 0.65             # swarm confidence in the probability estimate
    related_teams: List[str] = field(default_factory=list)
    stage: str = ""
    prop_type: str = ""   # match_winner | btts | over_under | clean_sheet |
                          # penalties | group_winner | tournament_winner | futures

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "market_type": self.market_type,
            "question": self.question,
            "short_title": self.short_title,
            "category": self.category,
            "subcategory": self.subcategory,
            "tags": self.tags,
            "yes_probability": round(self.yes_probability, 4),
            "no_probability": round(self.no_probability, 4),
            "outcomes": self.outcomes,
            "pricing": {
                "kalshi_yes_cents": round(self.kalshi_yes_cents, 1),
                "kalshi_no_cents": round(100 - self.kalshi_yes_cents, 1),
                "polymarket_yes_usdc": round(self.polymarket_yes_usdc, 4),
                "polymarket_no_usdc": round(1 - self.polymarket_yes_usdc, 4),
            },
            "resolution": {
                "criteria": self.resolution_criteria,
                "source": self.resolution_source,
                "date": self.resolution_date,
            },
            "platforms": self.platforms,
            "confidence": round(self.confidence, 3),
            "related_teams": self.related_teams,
            "stage": self.stage,
            "prop_type": self.prop_type,
        }

    def to_kalshi_format(self) -> Dict[str, Any]:
        """Format as a Kalshi contract listing."""
        return {
            "title": self.short_title,
            "subtitle": self.question,
            "ticker": self.question_id.upper(),
            "category": self.category,
            "close_time": f"{self.resolution_date}T23:59:00Z",
            "yes_price_cents": round(self.kalshi_yes_cents, 1),
            "no_price_cents": round(100 - self.kalshi_yes_cents, 1),
            "resolution_rules": self.resolution_criteria,
            "resolution_sources": [self.resolution_source],
            "tags": self.tags,
        }

    def to_polymarket_format(self) -> Dict[str, Any]:
        """Format as a Polymarket market listing."""
        return {
            "question": self.question,
            "description": self.resolution_criteria,
            "end_date": self.resolution_date,
            "outcomes": ["Yes", "No"],
            "outcome_prices": [
                round(self.polymarket_yes_usdc, 4),
                round(1 - self.polymarket_yes_usdc, 4),
            ],
            "category": f"{self.category} / {self.subcategory}",
            "tags": self.tags,
            "resolution_source": self.resolution_source,
        }

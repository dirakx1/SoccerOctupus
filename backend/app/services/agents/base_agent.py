"""Abstract base for all swarm prediction agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from ...models.match import AgentPrediction


class BaseFootballAgent(ABC):
    """
    Each agent in the swarm analyses a match from a specific angle.
    All agents share the same output contract (AgentPrediction) so the
    AggregatorAgent can combine them without knowing which agent produced which.
    """

    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight     # contribution weight for final aggregation

    @abstractmethod
    def predict(
        self,
        home_team: str,
        away_team: str,
        context: Dict[str, Any],
    ) -> AgentPrediction:
        """
        Args:
            home_team:  Team name string (must exist in TEAM_STATIC_DATA)
            away_team:  Team name string
            context:    Arbitrary extra context (stage, group, etc.)

        Returns:
            AgentPrediction with calibrated probabilities and reasoning.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} weight={self.weight}>"

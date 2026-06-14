"""
FifaOctopus configuration
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'app.db'}")
    CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY", "")
    CLERK_PUBLISHABLE_KEY: str = os.getenv("CLERK_PUBLISHABLE_KEY", "")
    CLERK_JWKS_URL: str = os.getenv(
        "CLERK_JWKS_URL",
        "https://api.clerk.com/v1/jwks",
    )
    CLERK_WEBHOOK_SECRET: str = os.getenv("CLERK_WEBHOOK_SECRET", "")
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3001")

    # LLM (OpenAI-compatible endpoint)
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o")

    # YouTube Data API v3
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")

    # SofaScore (unofficial public API — no key needed but respect rate limits)
    SOFASCORE_BASE_URL: str = "https://api.sofascore.com/api/v1"
    SOFASCORE_HEADERS: dict = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    # FBref / StatsBomb-style fallback data directory
    DATA_DIR: str = str(BASE_DIR / "data")

    # Storage
    UPLOAD_FOLDER: str = str(BASE_DIR / "uploads")
    PREDICTIONS_DIR: str = str(BASE_DIR / "uploads" / "predictions")

    # Opta / Stats Perform API (commercial license required)
    # API docs: https://developer.statsperform.com/
    # Without this key the collector falls back to derived Opta-style metrics.
    OPTA_API_KEY: str = os.getenv("OPTA_API_KEY", "")
    OPTA_BASE_URL: str = "https://api.performfeeds.com/soccerdata"

    # Zep Cloud — knowledge graph (mirrors MiroFish)
    # Free tier at https://app.getzep.com/ is sufficient for this use case
    ZEP_API_KEY: str = os.getenv("ZEP_API_KEY", "")
    ZEP_GRAPH_ID: str = os.getenv("ZEP_GRAPH_ID", "")   # pre-built graph; built on first run if empty

    # Flask
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", "5002"))

    # Swarm settings
    SWARM_PARALLEL_AGENTS: int = int(os.getenv("SWARM_PARALLEL_AGENTS", "5"))
    SWARM_TIMEOUT_SECONDS: int = int(os.getenv("SWARM_TIMEOUT_SECONDS", "60"))

    # Monte Carlo simulations per match
    MC_SIMULATIONS: int = int(os.getenv("MC_SIMULATIONS", "10000"))

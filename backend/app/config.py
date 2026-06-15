"""
FifaOctopus configuration
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")


def normalize_database_url(url: str) -> str:
    """Ensure PostgreSQL URLs use the psycopg3 driver."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Config:
    DATABASE_URL: str = normalize_database_url(
        os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/socceroctupus",
        )
    )
    CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY", "")
    CLERK_PUBLISHABLE_KEY: str = os.getenv("CLERK_PUBLISHABLE_KEY", "")
    CLERK_JWKS_URL: str = os.getenv(
        "CLERK_JWKS_URL",
        "https://api.clerk.com/v1/jwks",
    )
    CLERK_WEBHOOK_SECRET: str = os.getenv("CLERK_WEBHOOK_SECRET", "")
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3001")

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

    # Flask
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", "5002"))

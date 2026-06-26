"""
FifaOctopus configuration
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Z_][A-Z0-9_]{2,}=")

load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")


def normalize_database_url(url: str) -> str:
    """Ensure PostgreSQL URLs use the psycopg3 driver."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _normalize_multiline_value(value: str) -> str:
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        normalized = normalized[1:-1].strip()
    return normalized.replace("\\n", "\n")


def _read_raw_env_value(name: str, *paths: Path) -> str:
    prefix = f"{name}="
    for path in paths:
        if not path.exists():
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        collecting = False
        collected: list[str] = []

        for line in lines:
            if not collecting:
                if line.startswith(prefix):
                    first_value = line[len(prefix) :]
                    if "BEGIN PUBLIC KEY-----" not in first_value or "END PUBLIC KEY-----" in first_value:
                        return _normalize_multiline_value(first_value)

                    collected.append(first_value)
                    collecting = True
                continue

            if _ENV_ASSIGNMENT_RE.match(line):
                break

            collected.append(line)
            if line.strip().endswith("END PUBLIC KEY-----"):
                break

        if collected:
            return _normalize_multiline_value("\n".join(collected))

    return ""


def _load_clerk_jwt_public_key() -> str:
    configured_value = _normalize_multiline_value(os.getenv("CLERK_JWT_PUBLIC_KEY", ""))
    if configured_value and (
        "END PUBLIC KEY-----" in configured_value or "BEGIN PUBLIC KEY-----" not in configured_value
    ):
        return configured_value

    raw_value = _read_raw_env_value("CLERK_JWT_PUBLIC_KEY", BASE_DIR.parent / ".env", BASE_DIR / ".env")
    return raw_value or configured_value


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
    CLERK_JWKS_JSON: str = os.getenv("CLERK_JWKS_JSON", "")
    CLERK_JWT_PUBLIC_KEY: str = _load_clerk_jwt_public_key()
    CLERK_WEBHOOK_SECRET: str = os.getenv("CLERK_WEBHOOK_SECRET", "")
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3001")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_BASIC_PRICE_ID: str = os.getenv("STRIPE_BASIC_PRICE_ID", "")
    STRIPE_PRO_PRICE_ID: str = os.getenv("STRIPE_PRO_PRICE_ID", "")
    STRIPE_BILLING_PORTAL_CONFIGURATION_ID: str = os.getenv("STRIPE_BILLING_PORTAL_CONFIGURATION_ID", "")
    STRIPE_TEST_CLOCK_ID: str = os.getenv("STRIPE_TEST_CLOCK_ID", "")

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

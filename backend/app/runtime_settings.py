"""Runtime settings service."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from .db.models import AppSettings
from .secret_store import SecretStore

DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_MODEL_NAME = "gpt-4o"
DEFAULT_SWARM_PARALLEL_AGENTS = 7
DEFAULT_SWARM_TIMEOUT_SECONDS = 60
DEFAULT_MC_SIMULATIONS = 10000
DEFAULT_OPTA_BASE_URL = "https://api.performfeeds.com/soccerdata"


@dataclass(frozen=True)
class RuntimeSettings:
    llm_api_key: str
    llm_base_url: str
    llm_model_name: str
    youtube_api_key: str
    opta_api_key: str
    opta_base_url: str
    zep_api_key: str
    zep_graph_id: str
    swarm_parallel_agents: int
    swarm_timeout_seconds: int
    mc_simulations: int


class RuntimeSettingsService:
    @staticmethod
    def validate_payload(payload: dict) -> dict:
        data = {
            "llm_base_url": (payload.get("llm_base_url") or "").strip(),
            "llm_model_name": (payload.get("llm_model_name") or "").strip(),
            "zep_graph_id": (payload.get("zep_graph_id") or "").strip() or None,
            "opta_base_url": (payload.get("opta_base_url") or "").strip(),
            "swarm_parallel_agents": payload.get("swarm_parallel_agents"),
            "swarm_timeout_seconds": payload.get("swarm_timeout_seconds"),
            "mc_simulations": payload.get("mc_simulations"),
        }

        llm_parsed = urlparse(data["llm_base_url"])
        if not llm_parsed.scheme or not llm_parsed.netloc or not data["llm_base_url"].endswith("/v1"):
            raise ValueError("llm_base_url must be an absolute URL ending in /v1")
        if not data["llm_model_name"]:
            raise ValueError("llm_model_name is required")
        opta_parsed = urlparse(data["opta_base_url"])
        if not opta_parsed.scheme or not opta_parsed.netloc:
            raise ValueError("opta_base_url must be an absolute URL")

        for key in ("swarm_parallel_agents", "swarm_timeout_seconds", "mc_simulations"):
            try:
                data[key] = int(data[key])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{key} must be an integer") from exc

        if not 1 <= data["swarm_parallel_agents"] <= 7:
            raise ValueError("swarm_parallel_agents must be between 1 and 7")
        if data["swarm_timeout_seconds"] <= 0:
            raise ValueError("swarm_timeout_seconds must be greater than 0")
        if data["mc_simulations"] <= 0:
            raise ValueError("mc_simulations must be greater than 0")

        return data

    @staticmethod
    def ensure_defaults(db_session) -> AppSettings:
        settings = db_session.session.get(AppSettings, "global")
        if settings is None:
            settings = AppSettings(
                scope="global",
                llm_base_url=DEFAULT_LLM_BASE_URL,
                llm_model_name=DEFAULT_LLM_MODEL_NAME,
                zep_graph_id=None,
                opta_base_url=DEFAULT_OPTA_BASE_URL,
                swarm_parallel_agents=DEFAULT_SWARM_PARALLEL_AGENTS,
                swarm_timeout_seconds=DEFAULT_SWARM_TIMEOUT_SECONDS,
                mc_simulations=DEFAULT_MC_SIMULATIONS,
            )
            db_session.session.add(settings)
            db_session.session.commit()
        return settings

    @staticmethod
    def current(db_session) -> RuntimeSettings:
        settings = RuntimeSettingsService.ensure_defaults(db_session)
        secret_store = SecretStore()
        return RuntimeSettings(
            llm_api_key=secret_store.decrypt(settings.llm_api_key_encrypted),
            llm_base_url=settings.llm_base_url,
            llm_model_name=settings.llm_model_name,
            youtube_api_key=secret_store.decrypt(settings.youtube_api_key_encrypted),
            opta_api_key=secret_store.decrypt(settings.opta_api_key_encrypted),
            opta_base_url=settings.opta_base_url,
            zep_api_key=secret_store.decrypt(settings.zep_api_key_encrypted),
            zep_graph_id=settings.zep_graph_id or "",
            swarm_parallel_agents=settings.swarm_parallel_agents,
            swarm_timeout_seconds=settings.swarm_timeout_seconds,
            mc_simulations=settings.mc_simulations,
        )

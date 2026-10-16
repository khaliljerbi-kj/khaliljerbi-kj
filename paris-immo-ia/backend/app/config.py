from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://immo:immo@localhost:5432/immo"
    cors_origins: str = "http://localhost:3000"

    # "auto" : Anthropic si ANTHROPIC_API_KEY, sinon OpenAI si OPENAI_API_KEY,
    # sinon extracteur heuristique local (pratique pour développer sans clé).
    llm_provider: Literal["auto", "anthropic", "openai", "heuristic"] = "auto"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    whisper_model: str = "whisper-1"

    google_maps_api_key: str | None = None

    # Matching
    perfect_match_score: int = 75  # en dessous, on complète via les sources externes
    top_k: int = 3

    # Alertes
    alerts_interval_seconds: int = 0  # 0 = pas de boucle dans le process API
    alert_min_score: int = 90
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "alertes@paris-immo-ia.local"
    frontend_url: str = "http://localhost:3000"

    @property
    def sqlalchemy_url(self) -> str:
        # Prisma utilise "postgresql://", SQLAlchemy a besoin du driver explicite.
        url = self.database_url
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                url = "postgresql+psycopg://" + url.removeprefix(prefix)
        # "?schema=" est propre à Prisma ; les autres paramètres (sslmode de Neon…) sont gardés.
        return url.replace("?schema=public&", "?").split("?schema=")[0]


@lru_cache
def get_settings() -> Settings:
    return Settings()

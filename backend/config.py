from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = Field(...)
    voyage_api_key: str | None = None

    embeddings_provider: Literal["voyage", "local"] = "voyage"
    database_url: str = "sqlite:///./siach.db"
    chroma_dir: str = "./chroma_db"
    log_level: str = "INFO"

    anthropic_model_analise: str = "claude-sonnet-4-6"
    anthropic_model_humanizacao: str = "claude-haiku-4-5-20251001"
    voyage_model: str = "voyage-3-large"


def get_settings() -> Settings:
    return Settings()

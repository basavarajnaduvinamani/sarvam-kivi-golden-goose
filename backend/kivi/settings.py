from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="KIVI_",
        extra="ignore",
    )

    database_url: str = "sqlite:///./var/kivi.db"
    model_provider: str = "openai"
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_input_cost_per_million: float | None = None
    llm_output_cost_per_million: float | None = None
    embedding_cost_per_million: float | None = None

    def ensure_local_directories(self) -> None:
        if not self.database_url.startswith("sqlite:///"):
            return
        database_path = self.database_url.removeprefix("sqlite:///")
        if database_path == ":memory:":
            return
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


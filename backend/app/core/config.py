from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gogo Agent API"
    app_env: str = "local"
    litellm_model: str = "openai/gpt-4.1-mini"
    litellm_api_key: str | None = None
    openai_api_key: str | None = None
    enable_agent_tracing: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

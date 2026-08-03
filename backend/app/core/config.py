from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gogo Agent API"
    app_env: str = "local"
    litellm_model: str = "travel-primary"
    litellm_base_url: str | None = "http://127.0.0.1:4000"
    litellm_api_key: str | None = None
    openai_api_key: str | None = None
    enable_agent_tracing: bool = False

    @field_validator("litellm_base_url", "litellm_api_key", "openai_api_key", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

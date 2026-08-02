from agents.extensions.models.litellm_model import LitellmModel
from agents.run import RunConfig

from app.core.config import get_settings


def build_litellm_model() -> LitellmModel:
    settings = get_settings()
    api_key = settings.litellm_api_key or settings.openai_api_key
    return LitellmModel(model=settings.litellm_model, api_key=api_key)


def build_run_config() -> RunConfig:
    return RunConfig(model=build_litellm_model())

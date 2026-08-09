from agents.extensions.models.litellm_model import LitellmModel
from agents.run import RunConfig

from app.core.config import get_settings


def build_litellm_model() -> LitellmModel:
    settings = get_settings()
    api_key = settings.litellm_api_key or settings.openai_api_key
    return LitellmModel(
        model=settings.litellm_model,
        base_url=settings.litellm_base_url,
        api_key=api_key,
    )


def build_run_config(
    *,
    session_id: str | None = None,
    workflow_name: str = "gogo-agent",
) -> RunConfig:
    settings = get_settings()
    trace_metadata = {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "litellm_model": settings.litellm_model,
    }
    if session_id is not None:
        trace_metadata["session_id"] = session_id

    return RunConfig(
        model=build_litellm_model(),
        tracing_disabled=not settings.enable_agent_tracing,
        trace_include_sensitive_data=False,
        workflow_name=workflow_name,
        group_id=session_id,
        trace_metadata=trace_metadata,
    )

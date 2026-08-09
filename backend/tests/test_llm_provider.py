from app.core.config import get_settings
from app.providers.llm import build_litellm_model, build_run_config


def reset_settings(monkeypatch):
    for name in (
        "LITELLM_MODEL",
        "LITELLM_BASE_URL",
        "LITELLM_API_KEY",
        "OPENAI_API_KEY",
        "ENABLE_AGENT_TRACING",
        "APP_ENV",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()


def test_build_litellm_model_uses_proxy_base_url_when_configured(monkeypatch):
    reset_settings(monkeypatch)
    monkeypatch.setenv("LITELLM_MODEL", "travel-primary")
    monkeypatch.setenv("LITELLM_BASE_URL", "http://127.0.0.1:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "proxy-key")
    get_settings.cache_clear()

    model = build_litellm_model()

    assert model.model == "travel-primary"
    assert model.base_url == "http://127.0.0.1:4000"
    assert model.api_key == "proxy-key"


def test_build_litellm_model_keeps_direct_provider_fallback(monkeypatch):
    reset_settings(monkeypatch)
    monkeypatch.setenv("LITELLM_MODEL", "openai/gpt-4.1-mini")
    monkeypatch.setenv("LITELLM_BASE_URL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    get_settings.cache_clear()

    model = build_litellm_model()

    assert model.model == "openai/gpt-4.1-mini"
    assert model.base_url is None
    assert model.api_key == "openai-key"


def test_build_run_config_adds_trace_group_and_metadata(monkeypatch):
    reset_settings(monkeypatch)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LITELLM_MODEL", "travel-primary")
    get_settings.cache_clear()

    run_config = build_run_config(
        session_id="session-123",
        workflow_name="gogo-agent-intake",
    )

    assert run_config.workflow_name == "gogo-agent-intake"
    assert run_config.group_id == "session-123"
    assert run_config.trace_include_sensitive_data is False
    assert run_config.tracing_disabled is True
    assert run_config.trace_metadata == {
        "app_name": "Gogo Agent API",
        "app_env": "test",
        "litellm_model": "travel-primary",
        "session_id": "session-123",
    }


def test_build_run_config_can_enable_agent_tracing(monkeypatch):
    reset_settings(monkeypatch)
    monkeypatch.setenv("ENABLE_AGENT_TRACING", "true")
    get_settings.cache_clear()

    run_config = build_run_config(session_id="session-123")

    assert run_config.tracing_disabled is False

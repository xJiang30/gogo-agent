from app.core.config import get_settings
from app.providers.llm import build_litellm_model


def reset_settings(monkeypatch):
    for name in (
        "LITELLM_MODEL",
        "LITELLM_BASE_URL",
        "LITELLM_API_KEY",
        "OPENAI_API_KEY",
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

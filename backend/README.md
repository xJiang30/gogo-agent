# Gogo Agent Backend

FastAPI backend workspace for the real product implementation.

[中文说明](README.zh-CN.md)

The backend owns:

- Trip and proposal API boundaries
- OpenAI Agents SDK agent definitions
- LiteLLM model routing through one provider module
- Shared deterministic travel capabilities

## Commands

```bash
python --version  # requires Python >= 3.11
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest
```

Copy `.env.example` to `.env` and set the provider keys before running agent
calls.

## Model Gateway

The default path is:

```text
OpenAI Agents SDK -> LitellmModel -> LiteLLM Proxy -> model providers
```

Start the local LiteLLM Proxy with the example config:

```bash
export ZAI_API_KEY=...
litellm --config litellm.config.example.yaml
```

Then keep the backend pointed at the stable proxy alias:

```env
LITELLM_MODEL=travel-primary
LITELLM_BASE_URL=http://127.0.0.1:4000
LITELLM_API_KEY=local-proxy-key
```

To switch the underlying model, change `travel-primary` in the LiteLLM config
instead of changing agent code.

For quick local experiments without the proxy, leave `LITELLM_BASE_URL` empty
and use a provider-routed LiteLLM model string:

```env
LITELLM_MODEL=zai/glm-4.7-flash
LITELLM_BASE_URL=
ZAI_API_KEY=...
```

`pyproject.toml` remains the package metadata source. The requirements files are
kept for fast local setup and deployment environments that expect pip-style
dependency lists.

LiteLLM is capped below `1.75.0` for now to keep the local install lightweight
and avoid unexpectedly pulling a source build that needs Rust on macOS.

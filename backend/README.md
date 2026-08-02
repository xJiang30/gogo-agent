# Gogo Agent Backend

FastAPI backend workspace for the real product implementation.

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

`pyproject.toml` remains the package metadata source. The requirements files are
kept for fast local setup and deployment environments that expect pip-style
dependency lists.

LiteLLM is capped below `1.75.0` for now to keep the local install lightweight
and avoid unexpectedly pulling a source build that needs Rust on macOS.

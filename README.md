# Gogo Agent

AI-native travel planning MVP focused on conversational intake, an editable Trip
Board, map visualization, and proposal-first AI assistance.

[中文说明](README.zh-CN.md)

## Workspace Layout

```text
demo/       Static UX prototype used as the product interaction reference.
frontend/   Clean React + TypeScript product frontend workspace.
backend/    FastAPI backend with OpenAI Agents SDK and centralized LiteLLM.
docs/       Product and architecture specs.
```

The demo is intentionally separate from the production frontend. Use it to test
interaction ideas quickly, then rebuild stable flows in `frontend/` against the
real API contracts.

## Demo

```bash
python3 -m http.server 8765 --directory demo
node demo/tests/ux-regression.test.mjs
```

Then open `http://127.0.0.1:8765`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` when the backend is not running on
`http://127.0.0.1:8000`.

## Backend

```bash
cd backend
python --version  # requires Python >= 3.11
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest
```

Copy `backend/.env.example` to `backend/.env` and configure the LiteLLM Proxy
connection:

```env
LITELLM_MODEL=travel-primary
LITELLM_BASE_URL=http://127.0.0.1:4000
LITELLM_API_KEY=local-proxy-key
```

Start LiteLLM Proxy with:

```bash
cd backend
litellm --config litellm.config.example.yaml
```

Provider keys, such as `ZAI_API_KEY`, should be supplied through your local shell
or deployment secrets. Direct LiteLLM provider routing remains available by
leaving `LITELLM_BASE_URL` empty.

## Design

- [Chinese MVP design](docs/superpowers/specs/2026-07-07-ai-travel-agent-mvp-design.zh-CN.md)
- [High-level architecture](docs/superpowers/specs/2026-07-07-ai-travel-agent-high-level-architecture.zh-CN.md)
- [English MVP design](docs/superpowers/specs/2026-07-07-ai-travel-agent-mvp-design.md)

# Gogo Agent

AI-native travel planning MVP focused on conversational intake, an editable Trip
Board, map visualization, and proposal-first AI assistance.

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

Copy `backend/.env.example` to `backend/.env` and configure
`LITELLM_MODEL`, `LITELLM_API_KEY`, or `OPENAI_API_KEY` before real agent calls.

## Design

- [Chinese MVP design](docs/superpowers/specs/2026-07-07-ai-travel-agent-mvp-design.zh-CN.md)
- [High-level architecture](docs/superpowers/specs/2026-07-07-ai-travel-agent-high-level-architecture.zh-CN.md)
- [English MVP design](docs/superpowers/specs/2026-07-07-ai-travel-agent-mvp-design.md)

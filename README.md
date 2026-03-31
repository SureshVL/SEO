# OMNI-RANK OR-1 (Initial Build)

Production-oriented scaffold for a universal autonomous SEO system covering Google SEO, ASO, and social-distribution optimization.

## What is implemented now

- System architecture and modular backend/frontend/shared structure.
- Phase-1 **Algorithmic Reverse-Engineer Research Agent**.
- Phase-1 **ASO Agent** for localized store metadata and review-response playbooks.
- Phase-1 **LangGraph-style autonomous loop** (`SEOAutonomousLoop`) with score threshold checks.
- FastAPI endpoints wired for live research and ASO payload generation.
- Supabase SQL migration for required core tables.

## Repository layout

- `docs/system-architecture.md` — architecture + execution flow.
- `backend/app/agents/research_agent.py` — competitor reverse engineering logic.
- `backend/app/agents/aso_agent.py` — ASO metadata/review strategy generation.
- `backend/app/agents/workflow.py` — iterative scoring loop.
- `backend/app/clients/http_clients.py` — Serper/Firecrawl HTTP adapters.
- `backend/app/schemas/research.py` — research request/response models.
- `backend/app/schemas/aso.py` — ASO request/response models.
- `backend/app/main.py` — API bootstrap.
- `supabase/migrations/0001_omnirank_core.sql` — schema migration.

## Environment variables

Create `backend/.env`:

```env
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
SERPER_API_KEY=...
FIRECRAWL_API_KEY=...
SEO_SCORE_THRESHOLD=95
MAX_FEEDBACK_ITERATIONS=3
```

## Local setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# run tests
pytest

# run API
uvicorn app.main:app --reload
```

## API

### `POST /research/run`
Runs the autonomous research loop and returns:
- attempts used
- final score
- threshold status
- full research payload (competitors, gaps, recommendations)

> Requires `SERPER_API_KEY` and `FIRECRAWL_API_KEY`.

### `POST /aso/run`
Generates ASO metadata packs and review-response templates for the provided app link + locales.

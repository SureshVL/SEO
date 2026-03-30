# OMNI-RANK OR-1 (Initial Build)

Production-oriented scaffold for a universal autonomous SEO system covering Google SEO, ASO, and social-distribution optimization.

## What is implemented now

- System architecture and module map.
- Phase-1 **Algorithmic Reverse-Engineer Research Agent** in Python.
- Supabase SQL migration for core tables (`projects`, `competitor_intel`, `agent_logs`, `content_queue`).
- FastAPI service skeleton and unit test for research-agent logic.

## Repository layout

- `docs/system-architecture.md` — architecture, workflow, and scaling hooks.
- `backend/app/agents/research_agent.py` — competitor reverse engineering logic.
- `backend/app/schemas/research.py` — request/response contracts.
- `backend/app/main.py` — API bootstrap.
- `supabase/migrations/0001_omnirank_core.sql` — DB schema migration.

## Environment variables

Create `backend/.env`:

```env
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
SERPER_API_KEY=...
FIRECRAWL_API_KEY=...
```

## Local setup

```bash
# Python backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pydantic pydantic-settings pytest

# run tests
PYTHONPATH=. pytest -q

# run API
PYTHONPATH=. uvicorn app.main:app --reload
```

## Research Agent design notes

The research agent currently:
1. Pulls Top 3 SERP competitors via a pluggable Serper client.
2. Scrapes each page via a pluggable Firecrawl client.
3. Extracts page signals (headings, questions, entities, density).
4. Computes semantic/content gaps against the client page.
5. Produces weighted SEO score + prioritized recommendations.

## Next steps

- Wire real Serper + Firecrawl adapters with retry/backoff and rate limiting.
- Add LangGraph state machine for iterative self-scoring until 95+ threshold.
- Persist step-level events into `agent_logs` during each autonomous action.
- Implement ASO, Content, and Technical agents with shared score interface.

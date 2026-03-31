# OMNI-RANK OR-1 (Initial Build)

Production-oriented scaffold for a universal autonomous SEO system covering Google SEO, ASO, and social-distribution optimization.

## What was pending and is now implemented

- ✅ ASO agent implemented (localized metadata + review responses).
- ✅ Content agent implemented (Position-Zero draft generation into content queue payloads).
- ✅ Technical agent implemented (heuristic technical fix recommendations).
- ✅ Consolidated multi-agent orchestrator endpoint implemented (`/orchestrator/run`) with live log events.
- ✅ Existing research loop retained for iterative scoring toward threshold.

## Repository layout

- `backend/app/agents/research_agent.py` — competitor reverse engineering logic.
- `backend/app/agents/aso_agent.py` — ASO metadata/review strategy generation.
- `backend/app/agents/content_agent.py` — snippet-oriented content queue generator.
- `backend/app/agents/technical_agent.py` — technical SEO fix generator.
- `backend/app/agents/orchestrator_agent.py` — consolidated autonomous run controller.
- `backend/app/schemas/orchestrator.py` — unified orchestration request/response contracts.
- `backend/app/main.py` — FastAPI routes (`/research/run`, `/aso/run`, `/orchestrator/run`).

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
pytest
uvicorn app.main:app --reload
```

## API

### `POST /research/run`
Runs reverse-engineer loop and returns SEO score + research recommendations.

### `POST /aso/run`
Generates ASO metadata packs and review-response templates.

### `POST /orchestrator/run`
Runs research + technical + content (+ ASO when app context provided), returning:
- final score and cycle count
- live action logs
- technical fixes
- content queue items
- optional ASO payload

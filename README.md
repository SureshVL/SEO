# OMNI-RANK OR-1 (Next Phase)

## What is implemented now

- Durable async job lifecycle with SQLite-backed store.
- API-key protected orchestration endpoints (`X-API-KEY`).
- Retry/backoff hardened Serper + Firecrawl clients.
- Research pipeline persistence now stores scraped competitor markdown.
- Agents: Research, ASO, Content, Technical, Deploy bridge.
- Sync + async + SSE orchestration with shared execution path.
- Supabase-ready persistence for `agent_logs`, `competitor_intel`, `content_queue`.

## API

- `POST /research/run`
- `POST /jobs/research`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/stream`
- `POST /aso/run`
- `POST /deploy/run`

All non-health endpoints require `X-API-KEY`.

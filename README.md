# OMNI-RANK OR-1 (Next Phase)

## Implemented now (doable pending items)

- Durable async job lifecycle via SQLite-backed store.
- API-key protection (`X-API-KEY`) and request rate-limiting for orchestration routes.
- Retry/backoff + fallback endpoint support for Serper/Firecrawl clients.
- Research persistence now stores scraped competitor markdown in `competitor_intel`.
- ASO remediation execution in workflow when app context is provided (`app_link`, `app_name`, `app_category`).
- Deploy bridge endpoint supports dry-run and webhook-based submit flows for wordpress/shopify/appstore.
- Technical agent now returns queueable execution artifacts.
- Structured orchestrator logging for lifecycle events.

## API

- `POST /research/run`
- `POST /jobs/research`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/stream`
- `POST /aso/run`
- `POST /deploy/run`

All non-health endpoints require `X-API-KEY`.

## Quick bootstrap

```bash
./scripts/bootstrap_backend.sh
```

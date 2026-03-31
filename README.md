# OMNI-RANK OR-1 (Phase Complete)

## Completed in this pass

1. API-key auth upgraded with optional scoped key map (`ORCHESTRATOR_KEYS_JSON`).
2. Project-level access checks for protected research/job endpoints.
3. Rate limiting keyed by API key + client + path.
4. Durable SQLite job orchestration retained and hardened.
5. Provider retry/backoff with fallback endpoint support.
6. ASO remediation executes in-loop with defaults when app context is missing.
7. Technical remediation emits executable queue artifacts.
8. Deploy bridge supports dry-run + tokenized webhook submit flows.
9. Production guardrails: fail fast on default dev key and missing prod persistence.
10. Bootstrap/test path and docs retained for local verification.

## Core endpoints
- `POST /research/run`
- `POST /jobs/research`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/stream`
- `POST /aso/run`
- `POST /deploy/run`

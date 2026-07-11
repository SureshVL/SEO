# OMNI-RANK Security Audit

Pre-launch adversarial security review of the whole platform (FastAPI backend,
Next.js frontend, Supabase/Postgres). Three independent audit passes covered
auth/authorization/secrets/injection, SSRF/DoS/webhooks/public endpoints, and
frontend/CORS/headers/data-exposure.

Status legend: **FIXED** (remediated in this branch) · **MITIGATED** (risk
reduced, hardening recommended) · **TODO** (tracked follow-up).

---

## Critical

### C1. Supabase JWT signature was never verified — **FIXED**
`auth.py` decoded the JWT payload without checking the signature, accepted
`alg:none`, and treated `exp` as optional. Anyone could forge a token with any
`sub`/`role`. Now: HS256 signature verified with the Supabase JWT secret (stdlib
hmac, constant-time), `alg` pinned (no `none`), `exp` required; or, if no secret
is configured, the token is validated against Supabase `/auth/v1/user`.
Regression tests: `tests/test_security_hardening.py::TestJWTVerification`.

### C2. Backend API key shipped to the browser — **FIXED**
The store defaulted `apiKey` to `dev-orchestrator-key` and `NEXT_PUBLIC_API_KEY`,
both inlined into the JS bundle, giving any visitor full backend access. Now the
browser authenticates as the logged-in user via their Supabase JWT (`Authorization:
Bearer`); the shared key default is removed and documented as forbidden in the
frontend.

### C3. Cross-tenant access (shared key + trusted `X-Project-ID`) — **FIXED**
All requests used one shared key and selected the tenant with a client-supplied
header, and `_supabase_rest` uses the service-role key (bypassing RLS). Now a
verified JWT confines the request to the user's org: `_get_scoped_projects`,
`_org_filter`, and `_require_owned_project` scope every project lookup and the
by-id project endpoints to the caller's org; unknown/foreign ids 404. Service
(API-key) callers remain unconstrained for operator use.

### C4. SSRF via the public free-audit crawler — **FIXED**
`POST /public/audit` (unauthenticated) fetched an attacker-supplied host and
returned the crawled content, reachable at `169.254.169.254` (cloud metadata),
`localhost`, and private ranges, with redirect-following and no IP checks. Now a
shared SSRF guard (`app/core/ssrf.py`) resolves the host and rejects
private/loopback/link-local/reserved IPs, re-validates every redirect hop via a
guarded httpx transport, blocks non-http(s) schemes and dangerous ports, and caps
response size. Applied to the crawler, JS-render navigation, edge-verify, and
feed-import. Regression tests: `TestSSRF`.

---

## High

### H1. IDOR on by-id endpoints — **FIXED (projects) / MITIGATED (others)**
`get/update/delete project`, and other by-id routes, acted on a row with no
ownership check. Project routes now enforce org ownership. The remaining by-id
routes (keywords, content, link prospects, competitor/linking/audit/edge/git/feed
mutations) are covered defensively by the org-scoped RLS migration (H5) plus the
earlier project-scoping fixes; verify each is org-checked before public self-serve.

### H2. CORS `allow_origins=["*"]` with credentials — **FIXED**
Replaced with an explicit `CORS_ORIGINS` allowlist in production; the dev wildcard
now runs without credentials (a valid, safe combination).

### H3. XML entity-expansion (billion laughs / XXE) DoS — **FIXED**
Sitemap and feed XML used `xml.etree` (expands internal entities). Now
`safe_parse_xml` rejects any document declaring a DTD or entities and enforces a
size cap. Regression tests: `TestXMLGuard`.

### H4. No response-size cap on outbound fetches — **FIXED**
Crawler/edge/feed downloads are streamed with an 8 MB budget (`read_capped`),
preventing multi-GB memory-exhaustion responses.

### H5. RLS gaps and wrong ownership column — **FIXED (migration 0018)**
`org_invites`, `usage_metrics`, `credit_balances` had RLS disabled; feature-table
policies referenced a non-existent `projects.owner_user_ids`. Migration 0018
enables RLS everywhere and rebuilds every feature-table policy on the real
`org_id` model; `git_connections` stays deny-by-default (tokens never
client-readable).

### H6. OAuth/API tokens in localStorage — **MITIGATED / TODO**
GA4/GSC OAuth tokens and the API key were persisted in `localStorage` (XSS-stealable).
The API key is no longer defaulted or required client-side. **TODO:** move GA4/GSC
tokens server-side (encrypted) and have the backend make the Google calls.

---

## Medium

### M1. Public edge-config token injection + amplification — **FIXED**
`GET /edge/v1/config` interpolated the token into a PostgREST filter with only a
length check. Now the token must match `^or_[A-Za-z0-9_-]{1,80}$` before use.
Regression test: `TestEdgeTokenValidation`. (Rate limiting on this endpoint: TODO.)

### M2. PostgREST filter injection via unencoded params — **FIXED (hot paths)**
User input (URLs, keywords, timestamps, tokens, affected_url) is now percent-encoded
via `app/core/pgrest.q()` before entering query strings across wins, scheduler,
linking, keyword-mapping, multilingual, and edge services. **TODO:** sweep
remaining callers (CMS platform filter, link-prospect status) for the same pattern.

### M3. Razorpay webhook replay — **TODO**
Stripe enforces a timestamp tolerance; Razorpay does not de-duplicate event ids.
Recommend storing processed `x-razorpay-event-id` and rejecting replays. (Both
webhooks already verify HMAC signatures and no longer 500-loop.)

### M4. Verbose 500 error details — **FIXED**
59 handlers returned `detail=str(exc)` (leaking DB/PostgREST internals). All now
return a generic "Internal error"; full detail stays in server logs.

### M5. Missing security headers — **FIXED**
Added `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, and
HSTS (prod) via FastAPI middleware and `next.config.mjs` headers.

### M6. Startup fails open on default key — **FIXED**
The app now refuses to boot with the default/empty `ORCHESTRATOR_API_KEY` unless
`ENVIRONMENT=dev` and `ALLOW_DEFAULT_KEY=1`.

### M7. Prompt injection from feed content into exported feed — **TODO**
Poisoned product text can steer the optimizer's output (writes are already
constrained to the batch's own rows, so no cross-row pivot). Recommend delimiting
untrusted text as data and validating LLM output before export.

---

## Secrets at rest — **TODO**
GitHub PATs (`git_connections.access_token`) and CMS credentials are stored
plaintext (RLS-protected, never returned to clients, but readable via the
service-role path or a DB backup). Recommend envelope encryption (pgcrypto/KMS)
and minimal token scopes with rotation on disconnect.

---

## Rate limiting / DoS — **MITIGATED / TODO**
Public in-memory stores are now bounded, but the limiter is per-process and keyed
on the socket peer IP. For multi-worker/behind-a-proxy production: back the limiter
with Redis (fail closed), derive the client IP from a trusted forwarded-for hop,
and add rate limiting to `/edge/v1/config`.

---

## Verified NOT vulnerable
- Stripe & Razorpay webhook **signature** verification (constant-time HMAC;
  Stripe enforces timestamp tolerance and multi-`v1`).
- Git tokens stripped from all API responses; `git_connections` has no client RLS.
- File-read XXE not achievable (only entity-expansion DoS, now blocked).
- No open redirect (the `redirect` query param is never consumed).
- Service-role key is server-side only; the frontend uses the anon key.

## Recommended pre-public-launch order
1. Complete H6 (server-side OAuth tokens), Secrets-at-rest, M3 (webhook replay).
2. Finish the M2 param-encoding sweep and per-endpoint org checks for H1's tail.
3. Redis-backed rate limiting + `/edge/v1/config` throttle.
4. Penetration test against a staging deploy with real Supabase RLS enabled.

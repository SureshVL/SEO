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

### H6. OAuth/API tokens in localStorage — **FIXED**
GA4/GSC OAuth tokens and the API key were persisted in `localStorage`
(XSS-stealable). Now: the API key is no longer defaulted or persisted client-side;
GA4/GSC tokens are stored **encrypted server-side** (`oauth_tokens`, migration
0020) on OAuth exchange, are no longer returned to the browser, and are no longer
persisted in `localStorage`. The backend fetches them by `project_id` and refreshes
expired access tokens via the stored refresh token.

---

## Medium

### M1. Public edge-config token injection + amplification — **FIXED**
`GET /edge/v1/config` interpolated the token into a PostgREST filter with only a
length check. Now the token must match `^or_[A-Za-z0-9_-]{1,80}$` and the endpoint
has a per-IP rate limit (600/min). Regression test: `TestEdgeTokenValidation`.

### M2. PostgREST filter injection via unencoded params — **FIXED**
User input (URLs, keywords, timestamps, tokens, affected_url, CMS platform,
link-prospect status, content queue status) is percent-encoded via
`app/core/pgrest.q()` before entering query strings across all services.

### M3. Razorpay webhook replay — **FIXED**
The `webhook_events` table (migration 0019) records processed provider event ids
with a unique constraint; both Razorpay and Stripe handlers now reject duplicate
deliveries (fail-open on DB error so legitimate webhooks aren't dropped).

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

## Secrets at rest — **FIXED**
GitHub PATs (`git_connections.access_token`) and CMS `api_key`/`api_secret` are
now encrypted with Fernet envelope encryption (`app/core/secrets_crypto.py`)
using `SECRET_ENCRYPTION_KEY`, transparently on write and decrypt on use.
Backward compatible with existing plaintext rows; degrades to plaintext (with a
logged warning) only if no key is configured. Token scoping/rotation on
disconnect remains recommended operational hygiene.

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

## Remaining before public self-serve launch
Almost everything from the audit is now fixed. What's left is operational, not
code:
1. **Redis-backed rate limiting** for multi-worker/behind-proxy production (the
   current limiters are per-process; edge-config has a per-IP throttle but is
   also per-process). Derive the client IP from a trusted forwarded-for hop.
2. **Set the production secrets**: a strong `ORCHESTRATOR_API_KEY`,
   `SECRET_ENCRYPTION_KEY` (or credentials are stored plaintext), and
   `SUPABASE_JWT_SECRET`; run migrations 0018–0020.
3. **Penetration test** against a staging deploy with real Supabase RLS enabled.
4. Operational hygiene: minimal GitHub PAT scopes with rotation on disconnect;
   log scrubbing; per-tenant credential-read auditing.

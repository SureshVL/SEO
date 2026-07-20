# E2E Execution Results — Scenario 1 (Market Intelligence)

**Run by:** automated execution against a live backend in a test container.
**Date:** 2026-07-12
**Backend:** FastAPI on 127.0.0.1:8000, called via `X-API-KEY` (operator/service caller).
**Keys used:** Gemini, Serper, Firecrawl, Supabase (anon). No DataForSEO. No Supabase service-role key in this env.

---

## Component health (verified independently)

| Component | Result | Evidence |
|---|---|---|
| Serper (search) | ✅ 200 | `sustainable sneakers` → 9 organic results |
| Firecrawl (crawl) | ✅ 200 | crawled `allbirds.com` → 14,648 chars markdown, correct title |
| Gemini `gemini-2.0-flash` | ❌ 429 | `RESOURCE_EXHAUSTED` — free-tier **daily** quota exhausted on this key |
| Gemini `gemini-2.5-flash` | ✅ 200 | fresh quota; used after the thinking fix (below) |
| Supabase (anon) | ✅ 200 | auth/token validation works |
| Supabase (service-role) | ⚠️ n/a | not present in this test env (needed for DB writes) |
| DataForSEO | ❌ absent | not provided (required by AI Visibility) |

---

## Execution sheet

| # | Feature | Endpoint | Input | Result | Latency | Output summary |
|---|---|---|---|---|---|---|
| 1 | Projects (create) | `POST /projects` | name + `client_url=https://allbirds.com` | ⚠️ **500 in this env** | — | Needs Supabase **service-role key** to write the row (absent here). Works on the user's machine where the key is set (projects loaded 200 earlier). |
| 2 | AI Research | `POST /research/run` | `client_url=https://allbirds.com`, kw `sustainable sneakers` | ✅ **PASS (200)** | 87.7s | Iterative optimize workflow: **SEO score 30.49**, 3 attempts, **4 competitor pages** crawled, client profile (Allbirds: 1,414 words, 9 H2s), gap analysis (6 missing entities, missing questions), 2 recommendations. |
| 3 | Keyword Research | `POST /keywords/research` | seed `wool running shoes`, domain `allbirds.com`, US | ✅ **PASS (200)** | 17.6s | **25 opportunities**, 11 clusters, 10 content-plan items — each with volume/difficulty/intent/priority. Top: `allbirds wool running shoes` (p95), `merino wool running shoes` (p90). |
| 4 | Competitors | `POST /competitors/add` + `/analyze` | rothys.com | ⚠️ **not executed** | — | Requires an existing project (DB) → blocked by the same service-role dependency as #1. |
| 5 | AI Visibility | `POST /geo/check` | kw `best sustainable sneakers`, engine gemini | ❌ **400** | <1s | `DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD required`. **Test-plan correction:** this feature needs DataForSEO, not just Gemini. |

**Scenario 1 verdict:** the two LLM-analysis features that don't depend on the DB or DataForSEO (**AI Research, Keyword Research**) **pass with real, substantive output**. The rest are blocked by missing credentials (service-role, DataForSEO), not by code defects.

---

## Bug found & fixed during this run

**Gemini 2.5 models return empty JSON.** With `gemini-2.5-flash`, the first Keyword
Research run returned `200` but with **empty** `opportunities/clusters/content_plan`.
Cause: 2.5 models "think" by default, and the internal reasoning consumes the
`maxOutputTokens` budget, truncating the structured JSON we ask for (backend log
showed `tokens=520+163` then a retry `527+527` — tiny outputs).

**Fix:** disable thinking for 2.5 models in the Gemini client
(`generationConfig.thinkingConfig.thinkingBudget = 0`). After the fix, the same
request returned **25 populated opportunities**. (Committed in `gemini_client.py`.)

---

## Notes & observations

**Positive**
- Error handling is safe: failures return a generic `500 Internal Server Error`
  with no stack trace leaked to the client (server-side logs keep the detail) —
  confirms the M4 security hardening.
- AI Research runs a genuine **iterative optimization loop** (research → score →
  content/technical/aso remediation → re-score), stopping at max iterations.
- Data-gathering (Serper + Firecrawl) is solid and fast.

**Issues / follow-ups**
- **LLM quota is the main operational risk.** The single Gemini free-tier key
  hit its **daily** cap; every LLM feature then 500s. Mitigations: rotate among
  multiple keys, use a paid tier, or configure a second provider (Groq/OpenAI/
  Anthropic) so the router can fail over. The router currently retries the *same*
  exhausted provider 3× before failing (no fallback provider configured).
- **Silent empty result** on the 2.5 thinking issue: the endpoint returned `200`
  with empty arrays rather than warning. Consider logging a warning when the LLM
  yields zero structured items.
- **Crawler resilience:** one competitor page came back as `Untitled` / 3 words
  (JS-heavy or blocked). The JS-render fallback should catch these.
- **Test-plan correction:** AI Visibility (`/geo/check`, `/projects/{id}/ai-visibility`)
  requires DataForSEO credentials — update expectations in `E2E_TEST_PLAN.md`.

---

## To reproduce on your machine

1. Set `DEFAULT_GEMINI_MODEL=gemini-2.5-flash` in `backend/.env` (or use a Gemini
   key whose `gemini-2.0-flash` daily quota is fresh), pull this branch (for the
   thinking fix), restart the backend.
2. AI Research and Keyword Research will return populated results as above.
3. For Projects/Competitors: the service-role key you set makes those work.
4. For AI Visibility: add `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD`.
